"""Default implementation of the component manager api."""

from __future__ import annotations

import contextlib
import contextvars
import sys
import typing
import weakref

import attrs
import hikari
import hikari.components
from ryoshu import fields
# from ryoshu import interaction as interaction_impl
from ryoshu.api import component as component_api

if typing.TYPE_CHECKING:
    import typing_extensions

__all__: typing.Sequence[str] = ("ComponentManager", "get_manager", "check_manager")


_ROOT = sys.intern("root")
_COMPONENT_CTX: contextvars.ContextVar[tuple[component_api.ManagedComponent, str]] = contextvars.ContextVar("_COMPONENT_CTX")

T = typing.TypeVar("T")

CallbackWrapperFunc = typing.Callable[
    ["ComponentManager", component_api.ManagedComponent, hikari.InteractionCreateEvent],
    typing.AsyncGenerator[None, None],
]
CallbackWrapper = typing.Callable[
    ["ComponentManager", component_api.ManagedComponent, hikari.InteractionCreateEvent],
    typing.AsyncContextManager[None],
]
CallbackWrapperFuncT = typing.TypeVar("CallbackWrapperFuncT", bound=CallbackWrapperFunc)


ExceptionHandlerFunc = typing.Callable[
    ["ComponentManager", component_api.ManagedComponent, hikari.InteractionCreateEvent, Exception],
    typing.Coroutine[typing.Any, typing.Any, typing.Optional[bool]],
]
ExceptionHandlerFuncT = typing.TypeVar(
    "ExceptionHandlerFuncT", bound=ExceptionHandlerFunc
)

ComponentT = typing.TypeVar("ComponentT", bound=component_api.ManagedComponent)
ComponentType = type[component_api.ManagedComponent]


def _transform_select_options(
    options: typing.Sequence[hikari.SelectMenuOption]
) -> typing.Sequence[hikari.api.SelectOptionBuilder]:
    new_options: list[hikari.impl.SelectOptionBuilder] = []
    for option in options:
        builder = hikari.impl.SelectOptionBuilder(option.label, option.value, is_default=option.is_default)

        if option.description is not None:
            builder.set_description(option.description)

        if option.emoji is not None:
            builder.set_emoji(option.emoji)

        new_options.append(builder)

    return new_options


def _minimise_count(count: int) -> str:
    # We only need to support counts up to 25, as that is the
    # maximum number of components that can go on a message.
    # Byte-length 1 should support a range of 0~255 inclusive.
    byte = count.to_bytes(1, "little")
    # Decode into a charset that supports these bytes as a single char.
    return byte.decode("latin-1")


_COUNT_CHARS: typing.Final[tuple[str, ...]] = tuple(
    map(_minimise_count, range(25))
)
_DEFAULT_SEP: typing.Final[str] = sys.intern("|")
_DEFAULT_COUNT: typing.Final[typing.Literal[True]] = True


@attrs.define
class _ModuleData:
    name: str
    id: int

    @classmethod
    def from_object(cls, obj: object) -> typing_extensions.Self:
        module = sys.modules[obj.__module__]
        return cls(obj.__module__, id(module))

    def is_active(self) -> bool:
        if self.name not in sys.modules:
            return False

        return self.id == id(sys.modules[self.name])

    def is_reload_of(self, other: typing_extensions.Self) -> bool:
        return self.name == other.name and self.id != other.id


class ComponentManager(component_api.ComponentManager):
    """The standard implementation of a component manager.

    Component managers keep track of Ryoshu components and handle communication
    with hikari bots.

    To register a component to a component manager, use :meth:`register`.
    Without registering your components, they will remain unresponsive.

    To get an instance of a component manager, use :func:`get_manager`.

    Parameters
    ----------
    name:
        The name of the component manager. This should be unique for all live
        component managers.
    count:
        Whether the component manager should insert *one* count character to
        resolve duplicates. Normally, sending two components with the same
        custom id would error. Enabling this ensures custom ids are unique
        by appending an incrementing character. This costs 1 character,
        effectively reducing the maximum custom id length to 99 characters.

        If not set, the manager will use its parents' settings. The default
        set on the root manager is ``True``.
    sep:
        The character(s) to use as separator between custom id parts.

        If not set, the manager will use its parents' settings. The default
        set on the root manager is ``"|"``.
    bot:
        The bot to which to register this manager. This can be specified at any
        point through :meth:`.add_to_bot`.

    Examples
    --------
    Basic Ryoshu setup:
    ```py
    bot = hikari.GatewayBot(...)
    manager = ryoshu.get_manager()
    manager.add_to_bot(bot)

    @manager.register
    class MyButton(ryoshu.ManagedButton):
        ...
    ```

    """

    __slots__: typing.Sequence[str] = (
        "_bot",
        "_callback_wrapper",
        "_children",
        "_components",
        "_count",
        "_counter",
        "_exception_handler",
        "_identifiers",
        "_module_data",
        "_name",
        "_sep",
    )

    _bot: typing.Optional[hikari.GatewayBotAware]
    _children: typing.Set[ComponentManager]
    _components: weakref.WeakValueDictionary[str, ComponentType]
    _count: typing.Optional[bool]
    _counter: int
    _identifiers: dict[str, str]
    _module_data: dict[str, _ModuleData]
    _name: str
    _sep: typing.Optional[str]
    _callback_wrapper: typing.Optional[CallbackWrapper]
    _exception_handler: typing.Optional[ExceptionHandlerFunc]


    def __init__(
        self,
        name: str,
        *,
        count: typing.Optional[bool] = None,
        sep: typing.Optional[str] = None,
        bot: typing.Optional[hikari.GatewayBotAware] = None,
    ):
        self._bot = None
        self._name = name
        self._children = set()
        self._components = weakref.WeakValueDictionary()
        self._identifiers = {}
        self._count = count
        self._counter = 0
        self._module_data = {}
        self._sep = sep
        self._callback_wrapper = None
        self._exception_handler = None

        if bot:
            self.add_to_bot(bot)

    def __repr__(self) -> str:
        return f"ComponentManager(name={self.name})"

    @property
    def bot(self) -> hikari.GatewayBotAware:
        """The bot to which this manager is registered.

        If the manager has not yet been registered, this raises an exception.

        .. note::
            This is recursively accessed for all the parents of this manager.
            It is therefore generally recommended to set the bot on the root
            manager so that all other managers automatically have access to it.
        """
        bot = _recurse_parents_getattr(self, "_bot", None)
        if bot:
            return bot

        message = f"Component manager {self.name!r} is not yet registered to a bot."
        raise RuntimeError(message)

    @property
    def name(self) -> str:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        return self._name

    @property
    def children(self) -> typing.Set[ComponentManager]:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        return self._children

    @property
    def components(self) -> typing.Mapping[str, ComponentType]:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        return self._components

    @property
    def count(self) -> bool:
        """Whether or not this manager should add a count character to custom ids.

        This prevents discord from erroring when two components with equal
        parameters and thus equal custom ids are sent.

        By default, this is set to :obj:`True`. This can be changed using
        :meth:`config`.

        .. note::
            This is recursively checked for all the parents of this manager.
            For example, if ``get_manager("foo").count == True``, then its
            child ``get_manager("foo.bar").count`` will also return ``True``
            unless explicitly set to ``False``.

        .. warning::
            As this takes 1 character, the effective maximum custom id length
            is reduced to 99 characters.
        """
        # TODO: Add setter.
        return _recurse_parents_getattr(self, "_count", _DEFAULT_COUNT)

    @property
    def counter(self) -> int:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        return self._counter

    @property
    def sep(self) -> str:
        """The separator used to delimit parts of the custom ids of this manager.

        By default, this is set to "|". This can be changed using
        :meth:`config`.

        .. note::
            This is recursively accessed for all the parents of this manager.
        """
        # TODO: Add setter.
        return _recurse_parents_getattr(self, "_sep", _DEFAULT_SEP)

    @property
    def parent(self) -> typing.Optional[ComponentManager]:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        if "." not in self.name:
            # Return the root manager if this is not the root manager already.
            return None if self.name is _ROOT else get_manager(_ROOT)

        root, _ = self.name.rsplit(".", 1)
        return get_manager(root)

    def config(
        self,
        count: hikari.UndefinedNoneOr[bool] = hikari.UNDEFINED,
        sep: hikari.UndefinedNoneOr[str] = hikari.UNDEFINED,
    ) -> None:
        """Set configuration options on this manager."""
        if count is not hikari.UNDEFINED:
            self._count = count

        if sep is not hikari.UNDEFINED:
            self._sep = sep

    def make_identifier(self, component_type: ComponentType) -> str:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        return component_type.__name__

    def get_identifier(  # noqa: D102
        self, custom_id: str
    ) -> tuple[str, typing.Sequence[str]]:
        # <<docstring inherited from api.components.ComponentManager>>

        name, *params = custom_id.split(self.sep)

        if self.count and name.endswith(_COUNT_CHARS):
            # Count is always the single last character in the name part.
            return name[:-1], params

        return name, params

    def increment(self) -> str:  # noqa: D102
        count = _minimise_count(self._counter)

        self._counter += 1
        if self._counter > 24:
            self._counter = 0

        return count

    async def make_custom_id(self, component: component_api.ManagedComponent) -> str:
        # <<docstring inherited from api.components.ComponentManager>>

        identifier = self._identifiers[type(component).__name__]

        if self.count:
            identifier = identifier + self.increment()

        dumped_params = await component.factory.dump_params(component)

        return self.sep.join([identifier, *dumped_params.values()])

    async def parse_component_interaction(  # noqa: D102
        self, interaction: hikari.ComponentInteraction
    ) -> typing.Optional[component_api.ManagedComponent]:
        # <<docstring inherited from api.components.ComponentManager>>
        raw_component = next(iter(
            component
            for row in interaction.message.components
            for component in row
            if component.custom_id == interaction.custom_id
        ))
        return await self.parse_raw_component(raw_component, reference=interaction)

    async def parse_raw_component(
        self,
        component: typing.Union[hikari.components.ButtonComponent, hikari.components.SelectMenuComponent],
        /,
        *,
        reference: typing.Optional[object],
    ) -> typing.Optional[component_api.ManagedComponent]:
        """Parse a message component into a ryoshu component given a reference.

        .. note::
            This method only works for components registered to this manager or
            its parents.

        Parameters
        ----------
        component:
            The raw message component that is to be turned into a rich
            component.
        reference:
            The objects to use as reference in the parsers.

        Returns
        -------
        :class:`RichComponent`
            The newly created component.
        :obj:`None`:
            The provided component could not be parsed into a rich component
            that is registered to this manager.

        """
        custom_id = component.custom_id
        if not custom_id:
            return None

        identifier, params = self.get_identifier(custom_id)

        if identifier not in self._components:
            return None

        component_type = self._components[identifier]
        module_data = self._module_data[identifier]

        if not module_data.is_active():
            # NOTE: This occurs if:
            #       - The module on which the component is defined was unloaded.
            #       - The module on which the component is defined was reloaded
            #         and the component was never overwritten. It could either
            #         have been removed, or simply no longer be registered. The
            #         component *should* therefore be unresponsive.
            #
            #       Since we do not want to fire components that (to the user)
            #       do not exist anymore, we should remove them from the
            #       manager and return None.
            self.deregister_component(component_type)
            return None

        component_params: dict[str, typing.Any] = {
            field.name: getattr(component, field.name)
            for field in fields.get_fields(component_type, kind=fields.FieldType.INTERNAL)
        }

        if isinstance(component, hikari.components.TextSelectMenuComponent):
            component_params["options"] = _transform_select_options(component_params["options"])

        return await component_type.factory.build_component(reference, params, component_params=component_params)

    async def parse_message_components(
        self,
        message: hikari.Message,
        /,
    ) -> tuple[
        typing.Sequence[typing.Sequence[typing.Union[hikari.PartialComponent, component_api.ManagedComponent]]],
        typing.Sequence[component_api.ManagedComponent],
    ]:
        """Parse all components on a message into Ryoshu components where possible.

        This method is particularly useful if you wish to modify multiple
        components attached to a given message before sending them back.

        If called from within a component callback, this method will
        automatically use that same instance. This means that changes to
        ``self`` reflect on the sequences returned by this method, too.

        Parameters
        ----------
        message:
            The message of which to parse all components.

        Returns
        -------
        :class:`tuple`[:class:`Sequence`[:class:`Sequence`[:class:`Union`[:class:`hikari.PartialComponent`, :class:`ryoshu.api.ManagedComponent`]]], :class:`Sequence`[:class:`ryoshu.api.ManagedComponent`]]
            A tuple containing:

            - A nested structure of sequences that can be directly passed to
            :func:`ryoshu.into_action_rows`.

            - A sequence containing only the Ryoshu components to facilitate
            easier modification.

            These objects share the same component instances, so any changes
            made to components inside the separate sequence will also reflect
            on the nested structure.

        """  # noqa: E501
        new_rows: list[list[typing.Union[hikari.PartialComponent, component_api.ManagedComponent]]] = []
        rich_components: list[component_api.ManagedComponent] = []

        current_component, current_component_id = _COMPONENT_CTX.get((None, None))

        for row in message.components:
            new_row: list[typing.Union[hikari.PartialComponent, component_api.ManagedComponent]] = []
            new_rows.append(new_row)

            for component in row:
                if current_component is not None and component.custom_id == current_component_id:
                    rich_components.append(current_component)
                    new_row.append(current_component)
                    current_component = None  # Prevent re-entry.

                else:
                    new_component = await self.parse_raw_component(component, reference=message)    
                    if new_component:
                        rich_components.append(new_component)
                    
                    new_row.append(new_component or component)

        return new_rows, rich_components

    def register(self,
        *,
        identifier: typing.Optional[str] = None,
    ) -> typing.Callable[[type[ComponentT]], type[ComponentT]]:
        """Register a component to this component manager.

        This is the decorator interface to :meth:`register_component`.
        """
        def wrapper(component_type: type[ComponentT]) -> type[ComponentT]:
            return self.register_component(component_type, identifier=identifier)

        return wrapper

    def register_component(  # noqa: D102
        self,
        component_type: type[ComponentT],
        *,
        identifier: typing.Optional[str] = None,
    ) -> type[ComponentT]:
        # <<docstring inherited from api.components.ComponentManager>>
        resolved_identifier = identifier or self.make_identifier(component_type)
        module_data = _ModuleData.from_object(component_type)

        root_manager = get_manager(_ROOT)

        if resolved_identifier in root_manager._components:
            # NOTE: This occurs when a component is registered while another
            #       component with the same identifier already exists.
            #
            #       We now have two options:
            #       - This is caused by a reload. In this case, we expect the
            #         module name to remain unchanged and the module id to have
            #         changed. We can safely overwrite the old component.
            #       - This is an actual user error. If we were to silently
            #         overwrite the old component, it would unexpectedly go
            #         unresponsive. Instead, we raise an exception to the user.
            old_module_data = root_manager._module_data[resolved_identifier]
            if not module_data.is_reload_of(old_module_data):
                message = (
                    "Cannot register component with duplicate identifier"
                    f" {identifier!r}. (Original defined in module"
                    f" {old_module_data.name!r}, duplicate defined in module"
                    f" {module_data.name!r})"
                )
                raise RuntimeError(message)

        # Register to current manager and all parent managers.
        component_type.manager = self

        for manager in _recurse_parents(self):
            manager._components[resolved_identifier] = component_type
            manager._identifiers[component_type.__name__] = resolved_identifier
            manager._module_data[resolved_identifier] = module_data

        return component_type

    def deregister_component(self, component_type: ComponentType) -> None:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        identifier = self.make_identifier(component_type)
        component = self._components[identifier]

        if not component.manager:
            message = (
                f"Component {component_type.__name__!r} is not registered to a"
                " component manager."
            )
            raise TypeError(message)

        if not isinstance(component.manager, ComponentManager):
            # This should honestly never happen unless the user does some
            # really weird stuff.
            # TODO: Maybe think of an error message for this.
            raise TypeError

        # Deregister from the current manager and all parent managers.
        for manager in _recurse_parents(component.manager):
            manager._components.pop(identifier)
            manager._module_data.pop(identifier)

    def add_to_bot(self, bot: hikari.GatewayBotAware) -> None:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        # Ensure we don't duplicate the listeners.
        if _recurse_parents_getattr(self, "_bot", None) is not None:
            message = "This component manager is already registered to a bot."
            raise RuntimeError(message)

        bot.event_manager.subscribe(hikari.InteractionCreateEvent, self.invoke)

        self._bot = bot

    def remove_from_bot(self, bot: hikari.GatewayBotAware) -> None:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        # Bot.remove_listener silently ignores if the event doesn't exist,
        # so we manually handle raising an exception for it.
        if _recurse_parents_getattr(self, "_bot", None) is not None:
            message = "This component manager is not registered to this bot."
            raise RuntimeError(message)

        bot.event_manager.unsubscribe(hikari.InteractionCreateEvent, self.invoke)

    def as_callback_wrapper(self, func: CallbackWrapperFuncT) -> CallbackWrapperFuncT:
        """Register a callback as this managers' callback wrapper.

        A callback wrapper is essentially a function that is directly passed to
        ``contextlib.asynccontextmanager``. The ``yield`` statement releases
        control flow to the next manager, until the callback is finally invoked.

        Examples
        --------
        .. code-block:: python

            @manager.as_callback_wrapper
            async def wrapper(component, interaction):
                name = type(component).__name__
                print(f"User {interaction.user.display_name} invoked {name!r}.)
                yield
                print(f"Successfully ran callback for {name!r}.)

        Parameters
        ----------
        func:
            The callback to register. This must be an async function that takes
            the component manager as the first argument, the component as the
            second argument, and the interaction as the last. The function must
            have a single ``yield``-statement that yields ``None``.

        Returns
        -------
        Callable[[:class:`ManagedComponent`, :class:`hikari.InteractionCreateEvent`], AsyncGenerator[None, None]]
            The function that was just registered.

        """  # noqa: E501
        self._callback_wrapper = contextlib.asynccontextmanager(func)
        return func

    def as_exception_handler(self, func: ExceptionHandlerFuncT) -> ExceptionHandlerFuncT:
        """Register a callback as this manager's error handler.

        An error handler should take a component manager, a component, an
        interaction create event, and an exception.

        An error handler should return a boolean or ``None``:
        - ``True`` if the error was successfully handled and should not be
        propagated further.
        - ``False`` or ``None`` otherwise.

        Examples
        --------
        .. code-block:: python
            manager = get_manager()

            @manager.as_exception_handler
            async def ignore_type_errors(component, interaction, exception):
                if isinstance(exception, TypeError):
                    return True  # Silently ignore any TypeErrors

                return False  # Propagate all other errors.

        Parameters
        ----------
        func:
            The callback to register. This must be an async function that takes
            the component manager as the first argument, the component as the
            second, the interaction as the third, and the exception as the last.
            The function must return ``True`` to indicate that the error was
            handled successfully, or either ``False`` or ``None`` to indicate
            the opposite.

        Returns
        -------
        Callable[[:class:`RichComponent`, :class:`disnake.Interaction`, :class:`Exception`], None]
            The function that was just registered.

        """  # noqa: E501
        self._exception_handler = func
        return func

    async def invoke(self, event: hikari.InteractionCreateEvent) -> None:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        interaction = event.interaction
        if isinstance(interaction, hikari.ComponentInteraction):
            component = await self.parse_component_interaction(interaction)
            if not (component and component.manager):
                return

            # Set the contextvar for this invocation so that other methods can
            # use the same component instance and clear it afterwards.
            token = _COMPONENT_CTX.set((component, interaction.custom_id))
            try:
                # Invoke the component from the manager it was registered to.
                await component.manager.invoke_component(event, component)

            finally:
                _COMPONENT_CTX.reset(token)


    async def invoke_component(
        self,
        event: hikari.InteractionCreateEvent,
        component: component_api.ManagedComponent,
    ) -> None:  # noqa: D102
        # <<docstring inherited from api.components.ComponentManager>>

        # We need to traverse all managers twice so we store them in a list here.
        managers = list(_recurse_parents(self))
        try:
            # First we check every manager for a callback wrapper, and enter it
            # if one is found. This is done from root to the manager the
            # component is registered to.
            async with contextlib.AsyncExitStack() as stack:
                # Enter all the context managers...
                for manager in reversed(managers):
                    wrapper = manager.try_wrap_callback(component, event)
                    if wrapper is not None:
                        await stack.enter_async_context(wrapper)

                # If none raised, we run the callback.
                await component.callback(event)

        except Exception as exception:  # noqa: BLE001
            # We intentionally catch any non-BaseException here.
            # In case an exception occurred, try handling the error with error
            # handlers starting from the manager the component is registered to,
            # down to the root manager.
            for manager in managers:
                if await manager.try_handle_error(component, event, exception) is True:
                    return  # The error was handled successfully.

            # If the error remains unhandled, propagate it up to the listener
            # so that a hikari ExceptionEvent can be raised.

            # TODO: Wrap exception in a new exception that contains context
            #       (manager, component, original interaction, ...)
            raise

    def try_wrap_callback(
        self,
        component: component_api.ManagedComponent,
        event: hikari.InteractionCreateEvent,
    ) -> typing.Optional[typing.AsyncContextManager[None]]:
        if self._callback_wrapper is None:
            return None
        return self._callback_wrapper(self, component, event)

    async def try_handle_error(
        self,
        component: component_api.ManagedComponent,
        event: hikari.InteractionCreateEvent,
        exception: Exception,
    ) -> bool:
        if self._exception_handler is None:
            return False
        return await self._exception_handler(self, component, event, exception) or False

    def make_button(  # noqa: PLR0913
        self,
        identifier: str,
        *,
        as_root: bool = True,
        label: hikari.UndefinedOr[typing.Optional[str]] = hikari.UNDEFINED,
        style: hikari.UndefinedOr[hikari.ButtonStyle] = hikari.UNDEFINED,
        emoji: typing.Union[hikari.Snowflakeish, hikari.Emoji, str, hikari.UndefinedType] = hikari.UNDEFINED,
        disabled: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        **kwargs: object,
    ) -> component_api.ManagedButton:
        """Make an instance of the button class with the provided identifier.

        Parameters
        ----------
        as_root:
            Whether to use the root manager to get the component. This defaults
            to ``True`` so that any externally registered button can be built.
        identifier:
            The identifier of the button that is to be instantiated.
        label:
            The label to use. If not provided, uses the button class' default.
        style: disnake.ButtonStyle
            The style to use. If not provided, uses the button class' default.
        emoji:
            The emoji to use. If not provided, uses the button class' default.
        disabled:
            Whether or not to disable the button. If not provided, uses the
            button class' default.
        **kwargs:
            Any remaining keyword arguments are passed to the button's ``__init__``.

        Returns
        -------
        :class:`components.api.RichButton`
            The newly created button.

        Raises
        ------
        :class:`KeyError`
            The provided identifier does not belong to a registered component.
        :class:`TypeError`
            The provided identifier belongs to a component that is not a button.
        :class:`Exception`
            Any exception raised during button instantiation is propagated as-is.

        """
        if label is not hikari.UNDEFINED:
            kwargs["label"] = label
        if style is not hikari.UNDEFINED:
            kwargs["style"] = style
        if emoji is not hikari.UNDEFINED:
            kwargs["emoji"] = emoji
        if disabled is not hikari.UNDEFINED:
            kwargs["disabled"] = disabled

        manager = get_manager(_ROOT) if as_root else self
        component_type = manager.components[identifier]
        component = component_type(**kwargs)

        # NOTE: We sadly cannot use issubclass-- maybe make a custom issubclass
        #       implementation that works with protocols with non-method members
        #       given a couple assumptions.
        if isinstance(component, component_api.ManagedButton):
            return component

        message = (
            f"Expected identifier {identifier!r} to point to a button class,"
            f" got {component_type.__name__}."
        )
        raise TypeError(message)

    def make_select(  # noqa: PLR0913
        self,
        identifier: str,
        *,
        as_root: bool = True,
        placeholder: hikari.UndefinedOr[typing.Optional[str]] = hikari.UNDEFINED,
        min_values: hikari.UndefinedOr[int] = hikari.UNDEFINED,
        max_values: hikari.UndefinedOr[int] = hikari.UNDEFINED,
        disabled: hikari.UndefinedOr[bool] = hikari.UNDEFINED,
        options: hikari.UndefinedOr[list[hikari.impl.SelectOptionBuilder]] = hikari.UNDEFINED,
        **kwargs: object,
    ) -> component_api.ManagedSelectMenu:
        """Make an instance of the string select class with the provided identifier.

        Parameters
        ----------
        as_root:
            Whether to use the root manager to get the component. This defaults
            to ``True`` so that any externally registered select can be built.
        identifier:
            The identifier of the button that is to be instantiated.
        placeholder:
            The placeholder to use. If not provided, uses the select class' default.
        min_values:
            The minimum number of values a user is allowed to select. If not
            provided, uses the select class' default.
        max_values:
            The maximum number of values a user is allowed to select. If not
            provided, uses the select class' default.
        disabled:
            Whether or not to disable the button. If not provided, uses the
            select class' default.
        options:
            The options to use. If not provided, uses the select class' default.
        **kwargs:
            Any remaining keyword arguments are passed to the select's ``__init__``.

        Returns
        -------
        :class:`components.api.RichStringSelect`
            The newly created string select.

        Raises
        ------
        :class:`KeyError`
            The provided identifier does not belong to a registered component.
        :class:`TypeError`
            The provided identifier belongs to a component that is not a string select.
        :class:`Exception`
            Any exception raised during button instantiation is propagated as-is.

        """
        # NOTE: This currently only supports StringSelects

        if placeholder is not hikari.UNDEFINED:
            kwargs["placeholder"] = placeholder
        if min_values is not hikari.UNDEFINED:
            kwargs["min_values"] = min_values
        if max_values is not hikari.UNDEFINED:
            kwargs["max_values"] = max_values
        if disabled is not hikari.UNDEFINED:
            kwargs["disabled"] = disabled
        if options is not hikari.UNDEFINED:
            kwargs["options"] = options

        manager = get_manager(_ROOT) if as_root else self
        component_type = manager.components[identifier]
        component = component_type(**kwargs)

        if isinstance(component, component_api.ManagedSelectMenu):
            return component

        message = (
            f"Expected identifier {identifier!r} to point to a select class,"
            f" got {component_type.__name__}."
        )
        raise TypeError(message)


_MANAGER_STORE: typing.Final[dict[str, ComponentManager]] = {}


def _recurse_parents(manager: ComponentManager) -> typing.Iterator[ComponentManager]:
    yield manager
    while manager := manager.parent:  # pyright: ignore[reportAssignmentType]
        yield manager


def _recurse_parents_getattr(
    manager: ComponentManager, attribute: str, default: T
) -> T:
    for parent in _recurse_parents(manager):
        value = getattr(parent, attribute)
        if value is not None:
            return value

    return default


def get_manager(name: typing.Optional[str] = None) -> ComponentManager:
    """Get an existing manager by name, or create one if it does not yet exist.

    Calling :func:`get_manager` without specifying a name returns the root
    manager. The root manager is -- unless explicitly modified by the user --
    guaranteed to be the lowest-level manager, with no parents.

    Parameters
    ----------
    name: str
        The name of the component. If not provided, the root manager is
        returned.

    Returns
    -------
    :class:`ComponentManager`:
        A component manager with the desired name. If a component manager with
        this name already existed before calling this function, that same
        manager is returned. Otherwise, a new manager is created.

    """
    if name is None:
        # TODO: Maybe use a sentinel:
        #       - auto-infer name if sentinel,
        #       - return root logger if None was passed explicitly.
        name = _ROOT

    if name in _MANAGER_STORE:
        return _MANAGER_STORE[name]

    _MANAGER_STORE[name] = manager = ComponentManager(name)

    if "." in name:
        root, _ = name.rsplit(".", 1)
        parent = get_manager(root)
        parent.children.add(manager)

    return manager


def check_manager(name: str) -> bool:
    """Check if a manager with the provided name exists.

    .. note::
        Unlike :func:`get_manager`, this function will not create a manager
        if the provided name does not exist.

    Parameters
    ----------
    name:
        The name to check.

    Returns
    -------
    :class:`bool`
        Whether a manager with the provided name exists.

    """
    return name in _MANAGER_STORE
