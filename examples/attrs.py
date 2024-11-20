"""An example showcasing how attrs utilities can be used with Ryoshu."""

import os

import hikari
import ryoshu

bot = hikari.GatewayBot(os.environ["EXAMPLE_TOKEN"])

manager = ryoshu.get_manager()
manager.add_to_bot(bot)


@manager.register()
class CustomisableSelect(ryoshu.ManagedTextSelectMenu):
    def __attrs_post_init__(self) -> None:
        self.max_values = len(self.options)

    async def callback(self, event: hikari.InteractionCreateEvent) -> None:
        interaction = event.interaction
        assert isinstance(interaction, hikari.ComponentInteraction)

        selection = "\n".join(f"- {value}" for value in interaction.values) if interaction.values else "nothing :("

        await interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE,
            f"You selected:\n{selection}",
            flags=hikari.MessageFlag.EPHEMERAL,
        )


@bot.listen()
async def register_commands(event: hikari.StartingEvent):
    await bot.rest.set_application_commands(
        application=await bot.rest.fetch_application(),
        commands=[
            bot.rest
                .slash_command_builder("test_button", "test simple attrs functionality")
                .add_option(
                    hikari.CommandOption(
                        type=hikari.OptionType.STRING,
                        name="options",
                        description="The options for your select menu."
                    )
                ),
        ],
    )


@bot.listen()
async def handle_commands(event: hikari.InteractionCreateEvent) -> None:
    interaction = event.interaction
    if not isinstance(interaction, hikari.CommandInteraction):
        return

    options = interaction.options[0].value
    assert isinstance(options, str)

    if not options.strip():
        await interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_CREATE,
            "You must specify at least one option!",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    actual_options = [
        hikari.impl.SelectOptionBuilder(option, option)
        for option in map(str.strip, options.split(","))
    ]

    if len(actual_options) > 25:
        await interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_CREATE,
            f"You must specify at most 25 options! (Got {len(actual_options)}.)",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return

    await interaction.create_initial_response(
        hikari.ResponseType.MESSAGE_CREATE,
        component=await ryoshu.into_action_row(CustomisableSelect(options=actual_options)),
        flags=hikari.MessageFlag.EPHEMERAL,
    )


bot.run()
