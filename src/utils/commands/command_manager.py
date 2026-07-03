from utils.commands.command import Command, CommandSchema
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from casino.games import Game


class CommandManager:
    """A command manager that stores all available and executed commands for a game."""

    def __init__(self, game: Game):
        self.game = game

    def execute_command(self, command: CommandSchema):
        """Builds a command from the given schema, executes, and logs it."""
        command: Command = command.command_class(
            self.game, **{param.name: param.value for param in command.parameters}
        )

        command.execute()

    def get_command_by_index(self, index: int) -> CommandSchema:
        """Returns a CommandSchema based on the index of the command in the list of available commands."""
        return self.game.get_available_commands()[index]

    def get_commands(self):
        """Returns the list of available commands for the current game state."""
        return self.game.get_available_commands()
