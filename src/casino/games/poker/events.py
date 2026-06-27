from enum import Enum, auto


class PokerEvent(Enum):
    """Enumeration of events that can occur during a poker game."""

    BET_CHANGE = auto()
    """Event triggered when a player changes their bet."""
    START_HAND = auto()
    """Event triggered at the start of a new hand."""
    END_HAND = auto()
    """Event triggered at the end of a hand."""
    TURN = auto()
    """Event triggered when it's a player's turn to act."""
    DEAL_CARDS = auto()
    """Event triggered when cards are dealt."""
    CARD_HELD = auto()
    """Event triggered when a player holds a card."""
    CARDS_DISCARDED = auto()
    """Event triggered when a player discards cards."""
    HAND_OVER = auto()
    """Event triggered at the end of a hand, after winners have been determined and chips have been distributed."""
    HAND_RESET = auto()
    """Event triggered when a hand is reset, preparing for a new hand to start."""

class PokerCommandRequest(Enum):
    """Enumeration of commands that can be requested by the player in the Poker game."""

    NEW_HAND = auto()
    """Request to start a new hand."""
    START_ROUND = auto()
    """Request to start a new round of betting."""
    HOLD_CARD = auto()
    """Request to hold a specific card."""
    DISCARD_CARDS = auto()
    """Request to discard specific cards."""
    CHANGE_BET = auto()
    """Request to change the bet amount."""
    END_GAME = auto()
    """Request to end the game and exit the poker game."""
