from casino.player import PlayerController
from utils.event_listener import EventBus
from utils.commands.command_manager import CommandManager
from uuid import UUID

from casino.games.blackjack import BlackJackCommandRequest

class BlackjackPlayerController(PlayerController):
    """
    Controller for a Blackjack player, responsible for handling player actions and interactions with the game.
    This class can be extended to include additional functionality specific to Blackjack, such as managing the player's hand and calculating hand values.
    """

    def __init__(self, event_bus: EventBus, command_manager: CommandManager, player_id: UUID):
        super().__init__(event_bus, command_manager, player_id)

        self.event_bus.subscribe(BlackJackCommandRequest.HIT, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(BlackJackCommandRequest.STAND, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(BlackJackCommandRequest.PLACE_BET, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(BlackJackCommandRequest.REMOVE_BET, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(BlackJackCommandRequest.START_ROUND, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(BlackJackCommandRequest.RESET, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(BlackJackCommandRequest.END, lambda command_schema: self.execute_command(command_schema))
