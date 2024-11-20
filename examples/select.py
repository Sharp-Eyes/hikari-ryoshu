"""A simple example on the use of selects with Ryoshu."""

from __future__ import annotations

import os
import typing

import hikari
import ryoshu

bot = hikari.GatewayBot(os.environ["EXAMPLE_TOKEN"])

manager = ryoshu.get_manager()
manager.add_to_bot(bot)


LEFT = "\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}"
MIDDLE = "\N{BLACK CIRCLE FOR RECORD}\N{VARIATION SELECTOR-16}"
RIGHT = "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}"

SLOT_OPTIONS = [
    hikari.impl.SelectOptionBuilder(label="Left", value="left", emoji=LEFT),
    hikari.impl.SelectOptionBuilder(label="Middle", value="middle", emoji=MIDDLE),
    hikari.impl.SelectOptionBuilder(label="Right", value="right", emoji=RIGHT),
    hikari.impl.SelectOptionBuilder(label="Finalise", value="ok", emoji="\N{WHITE HEAVY CHECK MARK}"),
]


BLACK_SQUARE = "\N{BLACK LARGE SQUARE}"
BLUE_SQUARE = "\N{LARGE BLUE SQUARE}"
BROWN_SQUARE = "\N{LARGE BROWN SQUARE}"
GREEN_SQUARE = "\N{LARGE GREEN SQUARE}"
PURPLE_SQUARE = "\N{LARGE PURPLE SQUARE}"
RED_SQUARE = "\N{LARGE RED SQUARE}"
WHITE_SQUARE = "\N{WHITE LARGE SQUARE}"
YELLOW_SQUARE = "\N{LARGE YELLOW SQUARE}"

COLOUR_OPTIONS = [
    hikari.impl.SelectOptionBuilder(label="Black", value=BLACK_SQUARE, emoji=BLACK_SQUARE),
    hikari.impl.SelectOptionBuilder(label="Blue", value=BLUE_SQUARE, emoji=BLUE_SQUARE),
    hikari.impl.SelectOptionBuilder(label="Brown", value=BROWN_SQUARE, emoji=BROWN_SQUARE),
    hikari.impl.SelectOptionBuilder(label="Green", value=GREEN_SQUARE, emoji=GREEN_SQUARE),
    hikari.impl.SelectOptionBuilder(label="Purple", value=PURPLE_SQUARE, emoji=PURPLE_SQUARE),
    hikari.impl.SelectOptionBuilder(label="Red", value=RED_SQUARE, emoji=RED_SQUARE),
    hikari.impl.SelectOptionBuilder(label="White", value=WHITE_SQUARE, emoji=WHITE_SQUARE),
    hikari.impl.SelectOptionBuilder(label="Yellow", value=YELLOW_SQUARE, emoji=YELLOW_SQUARE),
]


@manager.register()
class MySelect(ryoshu.ManagedTextSelectMenu):
    placeholder: typing.Optional[str] = "Please select a square."
    options: typing.Sequence[hikari.impl.SelectOptionBuilder] = SLOT_OPTIONS

    slot: str = "0"
    state: str = "slot"
    colour_left: str = BLACK_SQUARE
    colour_middle: str = BLACK_SQUARE
    colour_right: str = BLACK_SQUARE

    async def callback(self, event: hikari.InteractionCreateEvent) -> None:
        assert isinstance(event.interaction, hikari.ComponentInteraction)
        selected = event.interaction.values[0]

        if self.state == "slot":
            self.handle_slots(selected)

        else:
            self.handle_colours(selected)

        content = self.render_colours()
        await event.app.rest.create_interaction_response(
            interaction=event.interaction,
            token=event.interaction.token,
            content=content,
            response_type=hikari.ResponseType.MESSAGE_UPDATE,
            component=await ryoshu.into_action_row(self),
        )

    def handle_slots(self, selected: str) -> None:
        if selected == "ok":
            self.disabled = True
            self.placeholder = "Woo!"
            print(self.options)
            return

        self.options = COLOUR_OPTIONS
        self.placeholder = f"Please select a colour for the {selected} square."

        self.slot = selected
        self.state = "colour"

    def handle_colours(self, selected: str) -> None:
        self.options = SLOT_OPTIONS
        self.placeholder = "Please select which slot to modify."

        setattr(self, f"colour_{self.slot}", selected)
        self.state = "slot"

    def render_colours(self) -> str:
        return f"{self.colour_left}{self.colour_middle}{self.colour_right}\n"


@bot.listen()
async def register_commands(event: hikari.StartingEvent):
    await bot.rest.set_application_commands(
        application=await bot.rest.fetch_application(),
        commands=[
            bot.rest.slash_command_builder("test_select", "test select menu"),
        ],
    )


@bot.listen()
async def handle_commands(event: hikari.InteractionCreateEvent) -> None:
    if not isinstance(event.interaction, hikari.CommandInteraction):
        return

    select = MySelect()

    await event.app.rest.create_interaction_response(
        interaction=event.interaction,
        token=event.interaction.token,
        content=select.render_colours(),
        response_type=hikari.ResponseType.MESSAGE_CREATE,
        component=await ryoshu.into_action_row(select),
    )


bot.run()
