from enum import Enum, auto
from dataclasses import dataclass


class SlotMachineEvents(Enum):
    """An enumeration of events that can occur in the Slot Machine game, used to notify listeners of changes in the game state."""

    SPIN = auto()
    """The player has spun the slot machine."""
    BET_CHANGE = auto()
    """The player has changed their bet amount."""
    MULTIPLIER_CHANGE = auto()
    """The player has changed their bet multiplier."""
    PLAYER_CHOICE = auto()
    """The player has made a choice (e.g., to spin, change bet, etc.)."""
    SPIN_START = auto()
    """A spin has started, and the reels are spinning."""
    SPIN_RESULT = auto()
    """The result of a spin has been determined, including the outcome and any winnings."""

class SlotMachineCommandRequest(Enum):
    """An enumeration of commands that can be requested by the player in the Slot Machine game."""

    SPIN = auto()
    """Request to spin the slot machine."""
    CHANGE_BET = auto()
    """Request to change the bet amount."""
    END_GAME = auto()
    """Request to end the game and exit the slot machine."""
