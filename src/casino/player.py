from dataclasses import dataclass
from uuid import UUID
from utils.commands.command import CommandSchema
from utils.commands.command_manager import CommandManager
from utils.event_listener import EventBus
from typing import Optional
from casino.games.generic_events import GenericEvent


@dataclass
class PlayerAccount:
    """
    A class representing a player's account, including their balance and methods to manage it.
    This is separate from the PlayerController to allow for more flexible account management
    and potential future features like multiple accounts per player or shared accounts.
    """

    id: UUID
    name: str
    balance: int

    def deposit(self, amount: int):
        """Deposit money into the player's account."""
        self.balance += amount

    def withdraw(self, amount: int) -> bool:
        """Withdraw money from the player's account. Returns True if successful, False if insufficient funds."""
        if 0 < amount <= self.balance:
            self.balance -= amount
            return True
        return False

    def buy_in(self, amount: int) -> Optional[PlayerBuyIn]:
        """Handles the buy-in process for a game. Returns The PlayerBuyIn object if successful, None if insufficient funds."""
        if self.withdraw(amount):
            return PlayerBuyIn(player_id=self.id, name=self.name, amount=amount)
        return None


@dataclass(frozen=True)
class PlayerView:
    """
    A class representing the player's view of the game, which can be used for rendering and for AI decision-making.
    This can include information about the player's hand, their current bet, and any other relevant details.
    """

    id: UUID
    name: str


@dataclass
class PlayerBuyIn:
    """
    A class representing a player's buy-in for a game, including the amount and any relevant details.
    This can be used to track how much a player has bought in for a specific game session, separate from their overall account balance.
    """

    player_id: UUID
    name: str
    amount: int


class PlayerController:
    """
    A class representing a player in a casino game.
    """

    event_bus: EventBus
    command_manager: CommandManager
    player_id: UUID
    is_my_turn: bool = False

    def __init__(
        self, event_bus: EventBus, command_manager: CommandManager, player_id: UUID
    ):
        self.event_bus = event_bus
        self.command_manager = command_manager
        self.player_id = player_id

        self.event_bus.subscribe(GenericEvent.TURN_START, self.on_turn)

    def on_turn(self, player_view: PlayerView):
        self.is_my_turn = self.player_id == player_view.id

    def execute_command(self, command_schema: CommandSchema):
        """Handles user input by looking up the corresponding command and executing it."""
        if self.is_my_turn:
            self.command_manager.execute_command(command_schema)
