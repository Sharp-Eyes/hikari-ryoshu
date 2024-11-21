"""An example on the use of select menus with Ryoshu."""

import enum
import os
import typing

import hikari

import ryoshu

bot = hikari.GatewayBot(os.environ["EXAMPLE_TOKEN"])

manager = ryoshu.get_manager()
manager.add_to_bot(bot)


class Slot(enum.Enum):
    LEFT = "\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}"
    MIDDLE = "\N{BLACK CIRCLE FOR RECORD}\N{VARIATION SELECTOR-16}"
    RIGHT = "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}"
    DONE = "\N{WHITE HEAVY CHECK MARK}"

SLOT_OPTIONS = [
    hikari.impl.SelectOptionBuilder(
        label=slot.name.title(),
        value=slot.name,
        emoji=slot.value,
    )
    for slot in Slot
]


class Colour(enum.Enum):
    BLACK = "\N{BLACK LARGE SQUARE}"
    RED = "\N{LARGE RED SQUARE}"
    GREEN = "\N{LARGE GREEN SQUARE}"
    BLUE = "\N{LARGE BLUE SQUARE}"

COLOUR_OPTIONS = [
    hikari.impl.SelectOptionBuilder(
        label=colour.name.title(),
        value=colour.name,
        emoji=colour.value,
    )
    for colour in Colour
]


class Colours(typing.NamedTuple):
    left: Colour
    middle: Colour
    right: Colour

    def replace(self, slot: Slot, colour: Colour) -> "Colours":
        return self._replace(**{slot.name.lower(): colour})

    def render(self) -> str:
        return "".join(colour.value for colour in self) + "\n"


@manager.register()
class SlotSelectMenu(ryoshu.ManagedTextSelectMenu):
    placeholder: typing.Optional[str] = "Please select a square."
    options: typing.Sequence[hikari.impl.SelectOptionBuilder] = SLOT_OPTIONS

    colours: Colours = Colours(Colour.BLACK, Colour.BLACK, Colour.BLACK)

    async def callback(self, event: hikari.InteractionCreateEvent) -> None:
        assert isinstance(event.interaction, hikari.ComponentInteraction)
        selected = Slot[event.interaction.values[0]]

        if selected == Slot.DONE:
            self.is_disabled = True
            component = self

        else:
            component = ColourSelectMenu(slot=selected, colours=self.colours)

        await event.interaction.create_initial_response(
            response_type=hikari.ResponseType.MESSAGE_UPDATE,
            content=self.colours.render(),
            component=await ryoshu.into_action_row(component),
        )


@manager.register()
class ColourSelectMenu(ryoshu.ManagedTextSelectMenu):
    options: typing.Sequence[hikari.impl.SelectOptionBuilder] = COLOUR_OPTIONS

    slot: Slot
    colours: Colours

    def __attrs_post_init__(self) -> None:  # See the `attrs.py` example.
        self.placeholder = f"Select a colour for the {self.slot.name.lower()} slot."

    async def callback(self, event: hikari.InteractionCreateEvent) -> None:
        assert isinstance(event.interaction, hikari.ComponentInteraction)
        selected = Colour[event.interaction.values[0]]

        new_colours = self.colours.replace(self.slot, selected)

        await event.interaction.create_initial_response(
            response_type=hikari.ResponseType.MESSAGE_UPDATE,
            content=new_colours.render(),
            component=await ryoshu.into_action_row(SlotSelectMenu(colours=new_colours)),
        )


@bot.listen()
async def register_commands(event: hikari.StartingEvent) -> None:
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

    select = SlotSelectMenu()

    await event.interaction.create_initial_response(
        content=select.colours.render(),
        response_type=hikari.ResponseType.MESSAGE_CREATE,
        component=await ryoshu.into_action_row(select),
    )


bot.run()
