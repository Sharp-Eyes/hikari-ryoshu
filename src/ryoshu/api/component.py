"""Protocols for components and component managers."""

from __future__ import annotations

import abc
import typing

import hikari
import hikari.components

if typing.TYPE_CHECKING:
    import typing_extensions

__all__: typing.Sequence[str] = (
    "ManagedComponent",
    "ManagedButton",
    # "RichSelectBuilder",
    "ComponentManager",
)


_T = typing.TypeVar("_T")

ComponentT = typing.TypeVar("ComponentT", bound="ManagedComponent")
"""A type hint for a (subclass of) a Ryoshu component.

In practice, this will be any implementation of the :class:`ManagedButton`,
or :class:`ManagedSelect` protocols.
"""


class ManagedComponent(abc.ABC):
    """Base class for all async component builder classes."""

    __slots__: typing.Sequence[str] = ()

    factory: typing.ClassVar[ComponentFactory[ManagedComponent]]
    manager: typing.ClassVar[typing.Optional[ComponentManager]]

    @abc.abstractmethod
    async def into_builder(self) -> hikari.api.ComponentBuilder:
        """Clone this builder to a new synchronous hikari-native ComponentBuilder.

        Returns
        -------
        hikari.api.ComponentBuilder
            The new synchronous hikari-native component builder.
        """

    @abc.abstractmethod
    async def build(self) -> typing.MutableMapping[str, typing.Any]:
        """Build a JSON object from this builder.

        Returns
        -------
        typing.MutableMapping[str, typing.Any]
            The built json object representation of this builder.
        """

    @abc.abstractmethod
    async def callback(self, event: hikari.InteractionCreateEvent, /) -> None:
        """Run the component callback.

        This should be implemented by the user in each concrete component type.

        Parameters
        ----------
        interaction:
            The interaction that caused this button to fire.

        """
        ...


class ManagedButton(ManagedComponent, abc.ABC):
    """Represents a Ryoshu-managed button component."""

    __slots__: typing.Sequence[str] = ()

    style: typing.Union[hikari.ButtonStyle, int]
    """Button's style."""

    emoji: typing.Union[hikari.Snowflakeish, hikari.Emoji, str, None]
    """Emoji which should appear on this button."""

    label: typing.Optional[str]
    """Text label which should appear on this button.

    !!! note
        The text label to that should appear on this button. This may be
        up to 80 characters long.
    """


class ManagedSelectMenu(ManagedComponent, abc.ABC):
    """Represents a Ryoshu-managed select component."""

    __slots__: typing.Sequence[str] = ()

    placeholder: typing.Optional[str]
    """Custom placeholder text shown if nothing is selected, max 100 characters."""

    min_values: int
    """The minimum amount of options which must be chosen for this menu.

    This will be greater than or equal to 0 and will be less than or equal to
    [`hikari.components.SelectMenuComponent.max_values`][].
    """

    max_values: int
    """The minimum amount of options which can be chosen for this menu.

    This will be less than or equal to 25 and will be greater than or equal to
    [`hikari.components.SelectMenuComponent.min_values`][].
    """

    is_disabled: bool
    """Whether the select menu is disabled."""


class ManagedTextSelectMenu(ManagedSelectMenu, abc.ABC):
    """Represents a Ryoshu-managed text select component."""

    options: typing.Sequence[hikari.impl.SelectOptionBuilder]
    """Sequence of up to 25 of the options set for this menu."""


class ManagedChannelSelectMenu(ManagedSelectMenu, abc.ABC):
    """Represents a Ryoshu-managed channel select component."""

    channel_types: typing.Sequence[hikari.ChannelType]
    """The valid channel types for this menu."""


class ComponentManager(typing.Protocol):
    """The baseline protocol for component managers.

    Component managers keep track of Ryoshu' special components
    and ensure they smoothly communicate with disnake's bots. Since this relies
    on listener functionality, component managers are incompatible with
    :class:`disnake.Client`-classes.

    To register a component to a component manager, use
    :meth:`register_component`. Without registering your components, they will
    remain unresponsive.
    """

    __slots__: typing.Sequence[str] = ()

    @property
    def name(self) -> str:
        """The name of this manager.

        Used in :func:`get_manager`. This functions similar to loggers, where a
        parent-child relationship is denoted with a ".". For example, a manager
        "foo.bar" has parent "foo", which has the root manager as parent.
        """
        ...

    @property
    def children(self) -> typing.Collection[ComponentManager]:
        """The children of this component manager."""
        ...

    @property
    def components(self) -> typing.Mapping[str, typing.Type[ManagedComponent]]:
        """The components registered to this manager or any of its children.

        In case a custom implementation is made, special care must be taken to
        ensure that these do not desync when a child's components are updated.
        """
        ...

    @property
    def parent(self) -> typing.Optional[ComponentManager]:
        """The parent of this manager.

        Returns :data:`None` in case this is the root manager.
        """
        ...

    def make_identifier(self, component_type: typing.Type[ManagedComponent], /) -> str:
        """Make an identifier for the provided component class.

        This is used to store the component in :attr:`components`, and to
        determine which component's callback should be fired when an interaction
        is received.

        Parameters
        ----------
        component_type
            The type of component for which to make an identifier.

        Returns
        -------
        str
            The component type's identifier.

        """
        ...

    def get_identifier(self, custom_id: str, /) -> typing.Tuple[str, typing.Sequence[str]]:
        """Extract the identifier and parameters from a custom id.

        This is used to check whether the identifier is registered in
        :attr:`components`.

        Parameters
        ----------
        custom_id
            The custom id from which to extract the identifier.

        """
        ...

    async def make_custom_id(self, component: ManagedComponent, /) -> str:
        """Make a custom id from the provided component.

        This can then be used later to reconstruct the component without any
        state or data loss.

        Parameters
        ----------
        component
            The component for which to create a custom id.

        Returns
        -------
        str
            A custom id that fully represents the provided component.

        """
        ...

    async def parse_component_interaction(
        self, interaction: hikari.ComponentInteraction, /
    ) -> typing.Optional[ManagedComponent]:
        """Parse an interaction and construct a rich component from it.

        In case the interaction does not match any component registered to this
        manager, this method will simply return :data:`None`.

        Parameters
        ----------
        interaction
            The interaction to parse. This should, under normal circumstances,
            be either a :class:`disnake.MessageInteraction` or
            :class:`disnake.ModalInteraction`.

        Returns
        -------
        :class:`RichComponent`
            The component if the interaction was caused by a component
            registered to this manager.
        :data:`None`
            The interaction was not related to this manager.

        """
        ...

    def register_component(self, component_type: typing.Type[ComponentT], /) -> typing.Type[ComponentT]:
        r"""Register a component to this component manager.

        This returns the provided class, such that this method can serve as a
        decorator.

        Parameters
        ----------
        component_type
            The component class to register.

        Returns
        -------
        :class:`type`\[:data:`.ComponentT`]
            The component class that was just registered.

        """
        ...

    def deregister_component(self, component_type: typing.Type[ManagedComponent], /) -> None:
        """Deregister a component from this component manager.

        After deregistration, the component will no be tracked, and its
        callbacks can no longer fire until it is re-registered.

        Parameters
        ----------
        component_type
            The component class to deregister.

        Returns
        -------
        type[RichComponent]
            The component class that was just deregistered.

        """

    def add_to_bot(self, bot: hikari.GatewayBot, /) -> None:
        """Register this manager to the provided bot.

        This is required to make components registered to this manager
        responsive.

        This method registers the :meth:`invoke` callback as an event to the
        bot for the :obj:`disnake.on_message_interaction` and
        :obj:`disnake.on_modal_submit` events.

        .. note::
            There is no need to separately register every manager you make.
            In general, it is sufficient to only register the root manager as
            the root manager will contain all components of its children.
            That is, the root manager contains *all* registered components, as
            every other manager is a child of the root manager.

        Parameters
        ----------
        bot
            The bot to which to register this manager.

        Raises
        ------
        RuntimeError
            This manager has already been registered to the provided bot.

        """
        ...

    def remove_from_bot(self, bot: hikari.GatewayBot, /) -> None:
        """Deregister this manager from the provided bot.

        This makes all components registered to this manager unresponsive.

        Parameters
        ----------
        bot
            The bot from which to deregister this manager.

        Raises
        ------
        RuntimeError
            This manager is not registered to the provided bot.

        """
        ...

    async def invoke(self, event: hikari.InteractionCreateEvent, /) -> None:  # noqa: D102
        """A"""

    async def invoke_component(self, event: hikari.InteractionCreateEvent, component: ManagedComponent) -> None:
        """Try to invoke a component with the given interaction.

        If this manager has no registered component that matches the interaction,
        it is silently ignored. Otherwise, the interaction will be parsed into
        a fully fledged component, and its callback will then be invoked.

        Parameters
        ----------
        interaction
            The interaction with which to try to invoke a component callback.

        """
        ...


class ComponentFactory(typing.Protocol[ComponentT]):
    """The baseline protocol for any kind of component factory.

    Any and all component factories must implement this protocol in order to be
    properly handled by Ryoshu.

    A component factory handles creating a component instance from a custom id
    by running all individual fields' parsers and aggregating the result into
    a component instance.
    """

    __slots__: typing.Sequence[str] = ()

    @classmethod
    def from_component(
        cls,
        component: typing.Type[ComponentT],
        /,
    ) -> typing_extensions.Self:
        """Create a component factory from the provided component.

        This takes the component's fields into account and generates the
        corresponding parser types for each field if a parser was not provided
        manually for that particular field.

        Parameters
        ----------
        component
            The component for which to create a component factory.

        """
        ...

    # TODO: Update docstring
    async def load_params(
        self,
        source: typing.Any,  # noqa: ANN401
        params: typing.Sequence[str],
        /,
    ) -> typing.Mapping[str, object]:
        """Create a new component instance from the provided custom id.

        This requires the custom id to already have been decomposed into
        individual fields. This is generally done using the
        :meth:`ComponentManager.get_identifier` method.

        Parameters
        ----------
        source
            The source object to use for creating the component instance.
        params
            A mapping of field name to to-be-parsed field values.

        """
        ...

    async def dump_params(self, component: ComponentT, /) -> typing.Mapping[str, str]:
        """Dump a component into a new custom id string.

        This converts the component's individual fields back into strings and
        and uses these strings to build a new custom id. This is generally done
        using the :meth:`ComponentManager.get_identifier` method.

        Parameters
        ----------
        component
            The component to dump into a custom id.

        """
        ...

    async def build_component(
        self,
        reference: typing.Any,  # noqa: ANN401
        params: typing.Sequence[str],
        component_params: typing.Optional[typing.Mapping[str, object]],
    ) -> ComponentT:
        """Create a new component instance from the provided interaction.

        This requires the custom id to already have been decomposed into
        individual fields. This is generally done by the component manager.

        Parameters
        ----------
        reference
            The reference object to use for creating the component instance.
        params
            A sequence of to-be-parsed field values.
        component_params
            A mapping of parameters that is to be directly passed to the
            component constructor.

        """
        ...
