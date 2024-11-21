"""Default implementation of select-based components."""

import abc
import typing

import hikari

from ryoshu import fields
from ryoshu.api import component as component_api
from ryoshu.impl.component import base as component_base

__all__: typing.Sequence[str] = (
    "ManagedTextSelectMenu",
    "ManagedUserSelectMenu",
    "ManagedRoleSelectMenu",
    "ManagedMentionableSelectMenu",
    "ManagedChannelSelectMenu",
)


class ManagedSelectMenu(component_api.ManagedSelectMenu, component_base.ComponentBase, abc.ABC):
    """The base class of a Ryoshu select menu.

    For implementations, see :class:`RichStringSelect`, :class:`RichUserSelect`,
    :class:`RichRoleSelect`, :class:`RichMentionableSelect`,
    :class:`RichChannelSelect`.
    """

    event: typing.ClassVar[str] = "on_dropdown"

    placeholder: typing.Optional[str] = fields.internal(default=None)
    min_values: int = fields.internal(default=1)
    max_values: int = fields.internal(default=1)
    is_disabled: bool = fields.internal(default=False)


class ManagedTextSelectMenu(ManagedSelectMenu, component_api.ManagedTextSelectMenu, abc.ABC):
    """The default implementation of a Ryoshu string select.

    This works similar to a dataclass, but with some extra things to take into
    account.

    First and foremost, there are class variables for :attr:`placeholder`,
    :attr:`min_values`, :attr:`max_values`, :attr:`disabled`, and:attr:`options`.
    These set the corresponding attributes on the select class when they are
    sent to discord, and are meant to be overwritten by the user.

    Fields can be defined similarly to dataclasses, by means of a name, a type
    annotation, and an optional :func:`components.field` to set the default or
    a custom parser. The options field specifically is designated with
    :func:`components.options` instead.

    Classes created in this way have auto-generated slots and an auto-generated
    ``__init__``. The init-signature contains all the custom id fields as
    keyword-only arguments.
    """

    options: typing.Sequence[hikari.impl.SelectOptionBuilder] = fields.internal(factory=list)

    async def into_builder(self) -> hikari.api.TextSelectMenuBuilder[typing.NoReturn]:
        # <<docstring inherited from component_base.ComponentBase>>
        return hikari.impl.TextSelectMenuBuilder(
            custom_id=await self.make_custom_id(),
            options=self.options,
            placeholder=hikari.UNDEFINED if self.placeholder is None else self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.is_disabled,
        )

    async def build(self) -> typing.MutableMapping[str, typing.Any]:
        # <<docstring inherited from component_base.ComponentBase>>
        return (await self.into_builder()).build()


class ManagedUserSelectMenu(ManagedSelectMenu, component_api.ManagedSelectMenu, abc.ABC):
    """The default implementation of a Ryoshu user select.

    This works similar to a dataclass, but with some extra things to take into
    account.

    First and foremost, there are class variables for :attr:`placeholder`,
    :attr:`min_values`, :attr:`max_values`, :attr:`disabled`.
    These set the corresponding attributes on the select class when they are
    sent to discord, and are meant to be overwritten by the user.

    Fields can be defined similarly to dataclasses, by means of a name, a type
    annotation, and an optional :func:`components.field` to set the default or
    a custom parser. The options field specifically is designated with
    :func:`components.options` instead.

    Classes created in this way have auto-generated slots and an auto-generated
    ``__init__``. The init-signature contains all the custom id fields as
    keyword-only arguments.
    """

    async def into_builder(self) -> hikari.api.SelectMenuBuilder:
        # <<docstring inherited from component_base.ComponentBase>>
        return hikari.impl.SelectMenuBuilder(
            type=hikari.ComponentType.USER_SELECT_MENU,
            custom_id=await self.make_custom_id(),
            placeholder=hikari.UNDEFINED if self.placeholder is None else self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.is_disabled,
        )

    async def build(self) -> typing.MutableMapping[str, typing.Any]:
        # <<docstring inherited from component_base.ComponentBase>>
        return (await self.into_builder()).build()


class ManagedRoleSelectMenu(ManagedSelectMenu, component_api.ManagedSelectMenu, abc.ABC):
    """The default implementation of a Ryoshu role select.

    This works similar to a dataclass, but with some extra things to take into
    account.

    First and foremost, there are class variables for :attr:`placeholder`,
    :attr:`min_values`, :attr:`max_values`, :attr:`disabled`.
    These set the corresponding attributes on the select class when they are
    sent to discord, and are meant to be overwritten by the user.

    Fields can be defined similarly to dataclasses, by means of a name, a type
    annotation, and an optional :func:`components.field` to set the default or
    a custom parser. The options field specifically is designated with
    :func:`components.options` instead.

    Classes created in this way have auto-generated slots and an auto-generated
    ``__init__``. The init-signature contains all the custom id fields as
    keyword-only arguments.
    """

    async def into_builder(self) -> hikari.api.SelectMenuBuilder:
        # <<docstring inherited from component_base.ComponentBase>>
        return hikari.impl.SelectMenuBuilder(
            type=hikari.ComponentType.ROLE_SELECT_MENU,
            custom_id=await self.make_custom_id(),
            placeholder=hikari.UNDEFINED if self.placeholder is None else self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.is_disabled,
        )

    async def build(self) -> typing.MutableMapping[str, typing.Any]:
        # <<docstring inherited from component_base.ComponentBase>>
        return (await self.into_builder()).build()


class ManagedMentionableSelectMenu(ManagedSelectMenu, component_api.ManagedSelectMenu, abc.ABC):
    """The default implementation of a Ryoshu mentionable select.

    This works similar to a dataclass, but with some extra things to take into
    account.

    First and foremost, there are class variables for :attr:`placeholder`,
    :attr:`min_values`, :attr:`max_values`, :attr:`disabled`.
    These set the corresponding attributes on the select class when they are
    sent to discord, and are meant to be overwritten by the user.

    Fields can be defined similarly to dataclasses, by means of a name, a type
    annotation, and an optional :func:`components.field` to set the default or
    a custom parser. The options field specifically is designated with
    :func:`components.options` instead.

    Classes created in this way have auto-generated slots and an auto-generated
    ``__init__``. The init-signature contains all the custom id fields as
    keyword-only arguments.
    """

    async def into_builder(self) -> hikari.api.SelectMenuBuilder:
        # <<docstring inherited from component_base.ComponentBase>>
        return hikari.impl.SelectMenuBuilder(
            type=hikari.ComponentType.MENTIONABLE_SELECT_MENU,
            custom_id=await self.make_custom_id(),
            placeholder=hikari.UNDEFINED if self.placeholder is None else self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.is_disabled,
        )

    async def build(self) -> typing.MutableMapping[str, typing.Any]:
        # <<docstring inherited from component_base.ComponentBase>>
        return (await self.into_builder()).build()


class ManagedChannelSelectMenu(ManagedSelectMenu, component_api.ManagedChannelSelectMenu, abc.ABC):
    """The default implementation of a Ryoshu channel select.

    This works similar to a dataclass, but with some extra things to take into
    account.

    First and foremost, there are class variables for :attr:`channel_types`,
    :attr:`placeholder`, :attr:`min_values`, :attr:`max_values`, :attr:`disabled`.
    These set the corresponding attributes on the select class when they are
    sent to discord, and are meant to be overwritten by the user.

    Fields can be defined similarly to dataclasses, by means of a name, a type
    annotation, and an optional :func:`components.field` to set the default or
    a custom parser. The options field specifically is designated with
    :func:`components.options` instead.

    Classes created in this way have auto-generated slots and an auto-generated
    ``__init__``. The init-signature contains all the custom id fields as
    keyword-only arguments.
    """

    channel_types: typing.Sequence[hikari.ChannelType] = fields.internal(factory=list)

    async def into_builder(self) -> hikari.api.ChannelSelectMenuBuilder:
        # <<docstring inherited from component_base.ComponentBase>>
        return hikari.impl.ChannelSelectMenuBuilder(
            custom_id=await self.make_custom_id(),
            placeholder=hikari.UNDEFINED if self.placeholder is None else self.placeholder,
            min_values=self.min_values,
            max_values=self.max_values,
            is_disabled=self.is_disabled,
            channel_types=self.channel_types,
        )

    async def build(self) -> typing.MutableMapping[str, typing.Any]:
        # <<docstring inherited from component_base.ComponentBase>>
        return (await self.into_builder()).build()
