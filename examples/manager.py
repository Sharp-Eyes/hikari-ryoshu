"""A simple example on the use of component managers with Ryoshu."""

import os
import typing

import attrs
import hikari
import ryoshu
import ryoshu.fields

bot = hikari.GatewayBot(os.environ["EXAMPLE_TOKEN"])

root_manager = ryoshu.get_manager()
root_manager.add_to_bot(bot)

shallow_manager = ryoshu.get_manager("foo")
nested_manager = ryoshu.get_manager("foo.bar.baz")


@shallow_manager.register()
class ShallowButton(ryoshu.ManagedButton):
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


@nested_manager.register()
class NestedButton(ryoshu.ManagedButton):
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


# A manager's callback wrapper applies to all components registered to it.
# Since a manager can see all of its children's components, a callback can
# effectively be wrapped by all its parents. Because the root manager is the
# parent of all managers, the following callback wrapper runs for ALL components.
@root_manager.as_callback_wrapper
async def wrapper(
    manager: ryoshu.ComponentManager,
    component: ryoshu.api.ManagedComponent,
    event: hikari.InteractionCreateEvent,
):
    # Do something before the component callback runs...
    assert isinstance(event.interaction, hikari.ComponentInteraction)
    username = event.interaction.user.display_name
    print(
        f"User {username!r} interacted with component"
        f" {type(component).__name__!r}..."
    )

    # Yield to run the component callback (and other wrappers)...
    yield

    # Do something after the component callback runs...
    print(
        f"User {username!r}s interaction with component"
        f" {type(component).__name__!r} was successful!"
    )


@attrs.define(auto_exc=True)
class InvalidUserError(Exception):
    message: str
    user: hikari.User


# Any component registered to (a child of) the nested manager will run the
# following wrapper. Note that we raise an exception in this wrapper.
@shallow_manager.as_callback_wrapper
async def check_wrapper(
    manager: ryoshu.api.ComponentManager,
    component: ryoshu.api.ManagedComponent,
    event: hikari.InteractionCreateEvent,
):
    # Ensure that the component is used by the same person who created the
    # component by means of an interaction earlier.
    interaction = event.interaction

    if (
        isinstance(interaction, hikari.ComponentInteraction)
        and interaction.message.interaction
        and interaction.user != interaction.message.interaction.user
    ):
        message = "You are not allowed to use this component."
        raise InvalidUserError(message, interaction.user)

    yield

# If an exception is raised in a component callback, the error handlers of its
# manager and all its parent managers are called sequentially, short-circuiting
# if any of them returns True. If an exception goes unhandled, hikari fires an
# ExceptionEvent as per usual.
# This exception handler handles the InvalidUserError raised in the above
# wrapper. Since it is registered to the nested manager, the shallow manager does
# NOT get this exception handler.
@nested_manager.as_exception_handler
async def error_handler(
    manager: ryoshu.ComponentManager,
    component: ryoshu.api.ManagedComponent,
    event: hikari.InteractionCreateEvent,
    exception: Exception,
):
    # Return True if the error was properly handled, and False otherwise.
    if isinstance(exception, InvalidUserError):
        await event.app.rest.create_interaction_response(
            interaction=event.interaction,
            token=event.interaction.token,
            response_type=hikari.ResponseType.MESSAGE_CREATE,
            content=f"{exception.user.mention}, {exception.message}",
            flags=hikari.MessageFlag.EPHEMERAL,
        )
        return True

    return False


# Standard hikari ExceptionEvent listener to validate that unhandled errors
# indeed propagate...
@bot.listen(hikari.ExceptionEvent)  # Workaround for generic typehint...
async def hikari_error_handler(event: hikari.ExceptionEvent[hikari.Event]):
    print("Exception handled by hikari:", repr(event.exception))


# Slash commands to test the components...
@bot.listen()
async def register_commands(event: hikari.StartingEvent):
    await bot.rest.set_application_commands(
        application=await bot.rest.fetch_application(),
        commands=[
            bot.rest.slash_command_builder("test_shallow_button", "test shallow nested manager"),
            bot.rest.slash_command_builder("test_nested_button", "test deeply nested manager"),
        ],
    )


@bot.listen()
async def handle_commands(event: hikari.InteractionCreateEvent) -> None:
    if not isinstance(event.interaction, hikari.CommandInteraction):
        return

    if event.interaction.command_name == "test_button":
        await event.app.rest.create_interaction_response(
            interaction=event.interaction,
            token=event.interaction.token,
            response_type=hikari.ResponseType.MESSAGE_CREATE,
            component=await ryoshu.into_action_row(ShallowButton()),
        )

    elif event.interaction.command_name == "test_nested_button":
        await event.app.rest.create_interaction_response(
            interaction=event.interaction,
            token=event.interaction.token,
            response_type=hikari.ResponseType.MESSAGE_CREATE,
            component=await ryoshu.into_action_row(NestedButton()),
        )


bot.run()
