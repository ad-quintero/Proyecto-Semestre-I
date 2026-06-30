from casino.player import PlayerController
from utils.event_listener import EventBus
from utils.commands.command_manager import CommandManager
from uuid import UUID

from casino.games.roulette.events import RouletteCommandRequest
from utils.commands.command import CommandSchema

class RoulettePlayerController(PlayerController):
    """
    Controller for a Roulette player, responsible for handling player actions and interactions with the game.
    This class can be extended to include additional functionality specific to Blackjack, such as managing the player's hand and calculating hand values.
    """

    def __init__(self, event_bus: EventBus, command_manager: CommandManager, player_id: UUID):
        super().__init__(event_bus, command_manager, player_id)

        self.event_bus.subscribe(RouletteCommandRequest.PLACE_BET, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(RouletteCommandRequest.REMOVE_BET, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(RouletteCommandRequest.SPIN_WHEEL, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(RouletteCommandRequest.END_GAME, lambda command_schema: self.execute_command(command_schema))
