from enum import Enum, auto


class PokerPhase(Enum):
    DEALING_CARDS = auto()
    """Phase where players are dealt their hole cards."""
    PLAYER_TURN = auto()
    """Phase where the active player takes their turn to act hold or discard cards."""
    SHOWDOWN = auto()
    """Phase where remaining players reveal their hands and the winner is determined."""
