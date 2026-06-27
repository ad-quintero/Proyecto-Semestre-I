from casino.player import PlayerController
from utils.event_listener import EventBus
from utils.commands.command_manager import CommandManager
from uuid import UUID

from casino.games.poker.events import PokerCommandRequest

class PokerPlayerController(PlayerController):
    """
    Controller for a Poker player, responsible for handling player actions and interactions with the game.
    This class can be extended to include additional functionality specific to the Poker game, such as managing the player's balance and tracking game outcomes.
    """

    def __init__(self, event_bus: EventBus, command_manager: CommandManager, player_id: UUID):
        super().__init__(event_bus, command_manager, player_id)

        self.event_bus.subscribe(PokerCommandRequest.NEW_HAND, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(PokerCommandRequest.START_ROUND, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(PokerCommandRequest.HOLD_CARD, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(PokerCommandRequest.DISCARD_CARDS, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(PokerCommandRequest.CHANGE_BET, lambda command_schema: self.execute_command(command_schema))
        self.event_bus.subscribe(PokerCommandRequest.END_GAME, lambda command_schema: self.execute_command(command_schema))
