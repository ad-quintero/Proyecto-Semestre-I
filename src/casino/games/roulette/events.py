from enum import Enum, auto

class RouletteEvents(Enum):
    """An enumeration of events that can occur in the Roulette game, used to notify listeners of changes in the game state."""

    PLAYER_TURN_START = auto()
    """The player's turn has started, allowing them to place bets."""
    INVALID_BET = auto()
    """An invalid bet was attempted, such as placing a bet with insufficient funds or on an invalid bet type."""
    BET_PLACED = auto()
    """A bet has been placed by the player."""
    BET_REMOVED = auto()
    """A bet has been removed by the player."""
    BETS_CLEARED = auto()
    """All bets have been cleared from the table."""
    SPIN_STARTED = auto()
    """The roulette wheel has started spinning."""
    SPIN_RESULT = auto()
    """The result of the spin has been determined, including the winning number and any payouts."""

class RouletteCommandRequest(Enum):
    """An enumeration of command requests that can be made by the player during their turn in the Roulette game."""

    PLACE_BET = auto()
    """Request to place a bet on the table."""
    REMOVE_BET = auto()
    """Request to remove a bet from the table."""
    CLEAR_BETS = auto()
    """Request to clear all bets from the table."""
    SPIN_WHEEL = auto()
    """Request to spin the roulette wheel."""
    END_GAME = auto()
    """Request to end the game and cash out the player's funds."""
