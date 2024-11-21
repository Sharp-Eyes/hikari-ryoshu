"""An example of having multiple Ryoshu components interact."""

import os
import typing

import hikari

import ryoshu

DEFAULT_OPTION = hikari.impl.SelectOptionBuilder("Please enable some options.", "placeholder", is_default=True)

bot = hikari.GatewayBot(os.environ["EXAMPLE_TOKEN"])

manager = ryoshu.get_manager()
manager.add_to_bot(bot)


@manager.register()
class OptionsToggleButton(ryoshu.ManagedButton):
    """A button component that enables/disables options on a DynamicSelectMenu."""

    style: typing.Union[hikari.ButtonStyle, int] = hikari.ButtonStyle.DANGER
    options: typing.Sequence[str]

    def parse_options(self) -> typing.Sequence[hikari.impl.SelectOptionBuilder]:
        if self.style == hikari.ButtonStyle.DANGER:
            return []

        return [hikari.impl.SelectOptionBuilder(option, option) for option in self.options]


    def update_select(self, components: typing.Sequence[ryoshu.api.ManagedComponent]) -> None:
        select: typing.Optional[DynamicSelectMenu] = None
        options: list[hikari.impl.SelectOptionBuilder] = []

        for component in components:
            if isinstance(component, DynamicSelectMenu):
                if select is not None:
                    msg = "Found more than one DynamicSelectMenu."
                    raise RuntimeError(msg)

                select = component

            elif isinstance(component, OptionsToggleButton):
                options.extend(component.parse_options())

        if not select:
            msg = "Could not find a DynamicSelectMenu."
            raise RuntimeError(msg)

        select.set_options(options)

    async def callback(self, event: hikari.InteractionCreateEvent) -> None:
        assert isinstance(event.interaction, hikari.ComponentInteraction)

        # Get all components on the message for easier re-sending.
        # Both of these lists will automagically contain self so that any
        # changes immediately reflect without extra effort.
        all_components, managed_components = await manager.parse_message_components(event.interaction.message)

        # Toggle style for the clicked button.
        self.style = (
            hikari.ButtonStyle.DANGER
            if self.style == hikari.ButtonStyle.SUCCESS
            else hikari.ButtonStyle.SUCCESS
        )

        # Add/remove options to the DynamicSelect based on whether this
        # button was toggled on or off.
        self.update_select(managed_components)

        # Re-send and update all components.
        await event.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE,
            components=await ryoshu.into_action_rows(all_components),
        )


@manager.register()
class DynamicSelectMenu(ryoshu.ManagedTextSelectMenu):
    """A select menu that has its options externally managed."""

    def __attrs_post_init__(self) -> None:  # See the `attrs.py` example.
        self.set_options([])

    def set_options(self, options: typing.Sequence[hikari.impl.SelectOptionBuilder]) -> None:
        if options:
            self.options = options
            self.max_values = len(options)
            self.is_disabled = False

        else:
            self.options = [DEFAULT_OPTION]
            self.max_values = 1
            self.is_disabled = True

    async def callback(self, event: hikari.InteractionCreateEvent) -> None:
        interaction = event.interaction
        assert isinstance(interaction, hikari.ComponentInteraction)

        selection = "\n".join(f"- {value}" for value in interaction.values) if interaction.values else "nothing :("

        await interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE,
            f"You selected:\n{selection}",
        )


@bot.listen()
async def register_commands(event: hikari.StartingEvent) -> None:
    await bot.rest.set_application_commands(
        application=await bot.rest.fetch_application(),
        commands=[
            bot.rest.slash_command_builder("test_components", "test working with multiple components"),
        ],
    )


@bot.listen()
async def handle_commands(event: hikari.InteractionCreateEvent) -> None:
    if not isinstance(event.interaction, hikari.CommandInteraction):
        return

    await event.interaction.create_initial_response(
        hikari.ResponseType.MESSAGE_CREATE,
        components=await ryoshu.into_action_rows(
            [
                [
                    OptionsToggleButton(label="numbers", options=["1", "2", "3", "4", "5"]),
                    OptionsToggleButton(label="letters", options=["a", "b", "c", "d", "e"]),
                    OptionsToggleButton(label="symbols", options=["*", "&", "#", "+", "-"]),
                ],
                [DynamicSelectMenu()],
            ],
        ),
    )


bot.run()
