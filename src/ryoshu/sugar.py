import typing

import hikari
import hikari.components

from ryoshu.api import component as component_api

__all__: typing.Sequence[str] = ("into_action_row", "into_action_rows")


async def into_builder(
    component: typing.Union[hikari.PartialComponent, hikari.api.ComponentBuilder, component_api.ManagedComponent],
) -> hikari.api.ComponentBuilder:
    if isinstance(component, hikari.api.ComponentBuilder):
        return component

    if isinstance(component, component_api.ManagedComponent):
        return await component.into_builder()

    if isinstance(component, hikari.ButtonComponent):
        if component.url is not None:
            return hikari.impl.LinkButtonBuilder(
                url=component.url,
                emoji=hikari.UNDEFINED if component.emoji is None else component.emoji,
                label=hikari.UNDEFINED if component.label is None else component.label,
                is_disabled=component.is_disabled,
            )
        if component.custom_id is not None:
            return hikari.impl.InteractiveButtonBuilder(
                style=component.style,
                custom_id=component.custom_id,
                emoji=hikari.UNDEFINED if component.emoji is None else component.emoji,
                label=hikari.UNDEFINED if component.label is None else component.label,
                is_disabled=component.is_disabled,
            )
        message = f"Got an unknown component type: {type(component).__name__!r}"
        raise TypeError(message)

    message = f"into_action_rows is not implemented for type {type(component).__name__!r}."
    raise TypeError(message)


async def into_action_row(
    *components: typing.Union[hikari.PartialComponent, hikari.api.ComponentBuilder, component_api.ManagedComponent],
) -> hikari.api.MessageActionRowBuilder:
    new_row = hikari.impl.MessageActionRowBuilder()
    for component in components:
        new_row.add_component(await into_builder(component))

    return new_row


async def into_action_rows(
    components: typing.Sequence[
        typing.Sequence[
            typing.Union[hikari.PartialComponent, hikari.api.ComponentBuilder, component_api.ManagedComponent]
        ]
    ],
) -> typing.Sequence[hikari.api.MessageActionRowBuilder]:
    return [await into_action_row(*row) for row in components]
