from enum import Enum, auto


class PokerEvent(Enum):
    """Enumeration of events that can occur during a poker game."""

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
