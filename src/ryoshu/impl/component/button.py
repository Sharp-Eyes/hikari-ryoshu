"""Default implementation of button-based components."""

import abc
import typing

import hikari
import hikari.impl.special_endpoints
import hikari.internal
import hikari.internal.attrs_extensions

from ryoshu import fields
from ryoshu.api import component as component_api
from ryoshu.impl.component import base as component_base

__all__: typing.Sequence[str] = ("ManagedButton",)


class ManagedButton(component_base.ComponentBase, component_api.ManagedButton, abc.ABC):
    """The default implementation of a Ryoshu interactive button.

    Fields can be defined similarly to attrs classes (~dataclasses), by means
    of a name, a type annotation, and an optional :func:`ryoshu.field`.

    ``__slots__`` and``__init__`` are automatically generated. If you need to
    customise initialisation, consider implementing ``__attrs_post_init__``.

    Default fields are:
    - label
    - style
    - emoji
    - is_disabled

    Any other fields will be interpreted as custom-id fields.

    """
    label: typing.Optional[str] = fields.internal(default=None)
    style: typing.Union[hikari.ButtonStyle, int] = fields.internal(default=hikari.ButtonStyle.SECONDARY)
    emoji: typing.Union[hikari.Snowflakeish, hikari.Emoji, str, None] = fields.internal(default=None)
    is_disabled: bool = fields.internal(default=False)

    async def into_builder(self) -> hikari.api.InteractiveButtonBuilder:
        # <<docstring inherited from component_base.ComponentBase>>
        return hikari.impl.InteractiveButtonBuilder(
            style=self.style,
            custom_id=await self.make_custom_id(),
            emoji=hikari.UNDEFINED if self.emoji is None else self.emoji,
            label=hikari.UNDEFINED if self.label is None else self.label,
            is_disabled=self.is_disabled,
        )

    async def build(self) -> typing.MutableMapping[str, typing.Any]:
        # <<docstring inherited from component_base.ComponentBase>>
        return (await self.into_builder()).build()
