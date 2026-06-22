from utils.commands.command import CommandSchema
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum
from .generic_events import GenericEvent
from utils.event_listener import EventBus
from uuid import UUID
from uuid import UUID
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from casino.player import PlayerBuyIn, PlayerView


class Game:
    """
    A base class for all casino games, providing common functionality and structure.
    """

    # A Finite State Machine. The current phase of the game, which can be used to manage game flow and logic.
    # This should be defined as an Enum in each specific game implementation.
    game_phase: Enum
    name: str

    def __init__(self, event_bus: EventBus, buy_in: PlayerBuyIn):
        self.event_bus = event_bus
        self.buy_in = buy_in

    @property
    @abstractmethod
    def active_player(self) -> UUID:
        """Returns the currently active player in the game."""
        pass

    def start(self):
        """Starts the game loop."""
        pass

    def change_phase(self, new_phase: Enum, snapshot: Snapshot = None):
        """
        Changes the current game phase and notifies listeners of the phase change.
        It sends the new phase and an optional snapshot of the game state to listeners as a tuple (new_phase, snapshot),
        allowing them to react accordingly (e.g., updating the UI, enabling/disabling commands).
        """
        self.game_phase = new_phase
        self.event_bus.notify(GenericEvent.PHASE_CHANGE, (new_phase, snapshot))

    def show_rules(self):
        raise NotImplementedError("Subclasses must implement the show_rules() method.")

    def get_available_commands(self) -> dict[Enum, CommandSchema]:
        """
        Returns a dict of CommandSchema objects representing the commands available in the current game state with
        their corresponding enum values that trigger the command as keys.
        """
        return []


@dataclass(frozen=True)
class Snapshot:
    """A snapshot of the game state at a specific point in time, used to pass around game state information."""

    active_player: PlayerView
