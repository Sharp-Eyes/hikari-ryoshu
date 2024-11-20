"""A simple example on the use of buttons with Ryoshu."""

import os
import typing

import hikari
import ryoshu

bot = hikari.GatewayBot(os.environ["EXAMPLE_TOKEN"])

manager = ryoshu.get_manager()
manager.add_to_bot(bot)


@manager.register()
class MyButton(ryoshu.ManagedButton):
    label: typing.Optional[str] = "0"
    count: int = 0

    async def callback(self, event: hikari.InteractionCreateEvent) -> None:
        assert isinstance(event.interaction, hikari.ComponentInteraction)

        self.count += 1
        self.label = str(self.count)

        await event.interaction.create_initial_response(
            hikari.ResponseType.MESSAGE_UPDATE,
            component=await ryoshu.into_action_row(self),
        )


@bot.listen()
async def register_commands(event: hikari.StartingEvent):
    await bot.rest.set_application_commands(
        application=await bot.rest.fetch_application(),
        commands=[
            bot.rest.slash_command_builder("test_button", "test simple counter button"),
        ],
    )


@bot.listen()
async def handle_commands(event: hikari.InteractionCreateEvent) -> None:
    if not isinstance(event.interaction, hikari.CommandInteraction):
        return

    await event.interaction.create_initial_response(
        hikari.ResponseType.MESSAGE_CREATE,
        component=await ryoshu.into_action_row(MyButton()),
    )


bot.run()
