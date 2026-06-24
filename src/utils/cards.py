from enum import Enum
import random
from dataclasses import dataclass
from typing import Optional


class Suit(Enum):
    """
    The suit of a playing card, which can be Hearts, Diamonds, Clubs, or Spades.
    """

    HEARTS = "♥️"
    DIAMONDS = "♦️"
    CLUBS = "♣️"
    SPADES = "♠️"


class Rank(Enum):
    """
    The rank of a playing card, which can be a number (2-10) or a face card (Jack, Queen, King, Ace).
    """

    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"


@dataclass
class Card:
    """
    A playing card with a suit and rank.
    """

    suit: Suit
    rank: Rank

    def __str__(self):
        return f"{self.rank.value}{self.suit.value}"

    @property
    def value(self) -> int:
        """Return the value of the card for games like Blackjack."""
        if self.rank in [Rank.JACK, Rank.QUEEN, Rank.KING]:
            return 10
        elif self.rank == Rank.ACE:
            return 11  # Ace can also be worth 1, but that logic is typically handled in the game rules
        else:
            return int(self.rank.value)


@dataclass
class CardView:
    """
    A view of a card that can be used for displaying the card to the player, which may include whether the card is face up or face down.
    """

    rank: Optional[Rank] = None  # None if face down
    suit: Optional[Suit] = None  # None if face down
    is_face_up: bool = False

    @classmethod
    def from_card(cls, card: Card, face_up=True):
        return cls(rank=card.rank, suit=card.suit, is_face_up=face_up)

    def __str__(self):
        if self.is_face_up:
            return f"{self.rank.value}{self.suit.value}"
        return "🂠"  # Back of the card


class Deck:
    """
    A standard deck of 52 playing cards, consisting of 4 suits (Hearts, Diamonds, Clubs, Spades) and 13 ranks (2-10, Jack, Queen, King, Ace).
    """

    cards: list[Card]

    def __init__(self, shuffle: bool = True):
        """
        intialize the deck with 52 cards and optionally shuffle it.
        """
        self.cards = [Card(suit, rank) for suit in Suit for rank in Rank]

        if shuffle:
            self.shuffle()

    def remaining_cards(self) -> int:
        """Return the number of remaining cards in the deck."""
        return len(self.cards)

    def shuffle(self):
        """Shuffle the deck of cards."""
        random.shuffle(self.cards)

    def deal(self, num_cards: int = 1, reshuffle=True) -> list[Card]:
        """
        Deal a specified number of cards from the top of the deck.

        If `reshuffle` then it generates a new deck if dealing clears it out, otherwise raises `ValueError` if there are not enough cards in the deck to deal.
        """

        if num_cards > len(self.cards) and not reshuffle:
            raise ValueError("Not enough cards in the deck to deal.")

        dealt_cards = self.cards[:num_cards]
        self.cards = self.cards[num_cards:]

        # If there are not enough cards to deal and reshuffling is allowed, reinitialize the deck and deal the remaining cards.
        if len(dealt_cards) < num_cards and reshuffle:
            self.__init__(True)  # Reinitialize the deck and shuffle it
            dealt_cards += self.deal(
                num_cards - len(dealt_cards), False
            )  # Deal the remaining cards without reshuffling again

        return dealt_cards
