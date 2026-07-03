from typing import TYPE_CHECKING, Optional

from casino.games import Game

if TYPE_CHECKING:
    from casino.games.poker.renderer import PokerTerminalRenderer

from utils.commands.command_manager import CommandManager
from utils.commands.command_manager import CommandManager
from utils.event_listener import EventBus
from utils.cards import Deck, Card, CardView
from casino.player import PlayerAccount
from dataclasses import dataclass
from itertools import combinations
from enum import IntEnum
from collections import Counter
from casino.games.game_manager import GameManager
from .phases import PokerPhase
from .events import PokerEvent
from . import commands
from uuid import UUID
from casino.games import Snapshot
from casino.player import PlayerBuyIn
from dataclasses import dataclass

from utils.commands.command import CommandSchema, CommandParameter
from casino.games.generic_events import GenericEvent
from casino.player import PlayerView
from casino.games.poker.events import PokerCommandRequest
from casino.games.poker.player_controller import PokerPlayerController


@dataclass
class PokerPlayer:
    id: UUID
    name: str
    cards: list[Card]
    funds: float = 0

    def to_view(self, cards_visible: bool = False) -> PokerPlayerView:
        return PokerPlayerView(
            id=self.id,
            name=self.name,
            cards=[CardView(c.rank, c.suit, cards_visible) for c in self.cards],
            funds=self.funds,
        )


@dataclass(frozen=True)
class PokerPlayerView(PlayerView):
    cards: list[CardView]
    funds: float


@dataclass(frozen=True)
class PokerSnapshot(Snapshot):
    active_player: PokerPlayerView
    """The current dealer's data."""
    community_cards: list[CardStateView]
    """A list of the community cards on the table."""
    bet: float
    """The bet for the current hand."""
    payout_multiplier: Optional[int] 
    """The multiplier of the bet earnings. Included only on hand end."""
    final_hand: Optional[tuple[HandRank, list[CardStateView]]]
    """The rank and tie-breaker vector of the player's final hand, determined at the end"""
    available_commands: dict[PokerCommandRequest, CommandSchema]
    """The list of available commands for the current active player, which can be used for rendering the UI and for AI decision-making."""


class HandRank(IntEnum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9

payout_table = {
    HandRank.HIGH_CARD: 0,
    HandRank.PAIR: 1,
    HandRank.TWO_PAIR: 2,
    HandRank.THREE_OF_A_KIND: 3,
    HandRank.STRAIGHT: 4,
    HandRank.FLUSH: 6,
    HandRank.FULL_HOUSE: 9,
    HandRank.FOUR_OF_A_KIND: 25,
    HandRank.STRAIGHT_FLUSH: 50,
    HandRank.ROYAL_FLUSH: 800,
}

class CardRank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14


class PokerManager(GameManager):
    def __init__(
        self,
        game: Poker,
        player: PlayerAccount,
        renderer: PokerTerminalRenderer,
        player_buy_in: PlayerBuyIn,
    ):
        self.event_bus = EventBus()
        self.renderer = renderer(self.event_bus)

        self.game = game(self.event_bus, player_buy_in)

        self.command_manager = CommandManager(self.game)

        self.player = PokerPlayerController(self.event_bus, self.command_manager, player.id)

@dataclass
class CardState:
    card: Card
    hold: bool

@dataclass
class CardStateView:
    card: CardView
    hold: bool

class Poker(Game):
    deck: Deck
    """The deck used in the game"""

    community_cards: list[CardState]
    """The community cards on the table. A player can choose to hold or discard any number cards."""

    player: PokerPlayer
    """The human player in the game"""

    bet: float
    """The bet for the current hand"""

    def __init__(
        self, event_bus: EventBus, buy_in: PlayerBuyIn
    ):
        super().__init__(event_bus, buy_in)

        self.player = PokerPlayer(
            id=buy_in.player_id, name=buy_in.name, cards=[], funds=buy_in.amount
        )
        
        self.deck = Deck()
        self.community_cards = []
        self.bet = 0
        self.payout_multiplier = None 
        # They payout multiplier is determined at the end of the hand based on the hand rank, 
        # and is used to calculate the final earnings from the bet. It is included in the snapshot only 
        # at the end of the hand, since it is not relevant during the hand.

        self.game_phase = None

    @property
    def active_player(self) -> PokerPlayer:
        """Returns the current player."""
        return self.player
    
    def start(self):
        # Reset all game state for the new hand
        self.deck = Deck()
        self.community_cards = []

        # If the player ended the last hand with a bet, we carry it over to the new hand as a starting bet,
        # capping it to the player's available funds, and ensuring it's not negative
        self.bet = min(0, self.bet, self.player.funds) 

        self.change_phase(PokerPhase.PLAYER_TURN, self.get_snapshot())
        self.event_bus.notify(GenericEvent.TURN_START, self.player.to_view())
        self.event_bus.notify(GenericEvent.GAME_START, self.get_snapshot())
        self.event_bus.notify(PokerEvent.TURN, self.get_snapshot())


    def start_round(self):
        self.deal_cards()

    def end(self):
        pass

    def change_bet(self, amount: float):
        # Calculate what the new bet *would* be
        proposed_bet = self.bet + amount
    
        # 🎯 RULE 1: The bet cannot drop below 0
        # 🎯 RULE 2: The bet cannot exceed the player's current total cash
        if 0 <= proposed_bet <= self.player.funds:
            self.bet = proposed_bet

            self.event_bus.notify(PokerEvent.BET_CHANGE, self.get_snapshot())

            self.event_bus.notify(
                GenericEvent.TURN_START,
                self.player.to_view(),
            )
            self.event_bus.notify(PokerEvent.TURN, self.get_snapshot())
        else:
            raise ValueError(f"Invalid bet change: {amount}. Proposed bet would be {proposed_bet}, but player funds are {self.player.funds}.")

    def deal_cards(self):
        """Deals the starting 5 hands."""

        self.player.funds -= self.bet
        self.change_phase(PokerPhase.DEALING_CARDS)

        self.community_cards = [CardState(card, False) for card in self.deck.deal(5)]

        self.change_phase(PokerPhase.PLAYER_TURN)
        self.event_bus.notify(PokerEvent.DEAL_CARDS, self.get_snapshot())
        self.event_bus.notify(GenericEvent.TURN_START, self.player.to_view())
        self.event_bus.notify(PokerEvent.TURN, self.get_snapshot())

    def hold_card(self, idx):
        """
            Marks the card at the given index for holding.
        """
        self.community_cards[idx].hold = True

        self.event_bus.notify(PokerEvent.CARD_HELD, self.get_snapshot())
        self.event_bus.notify(GenericEvent.TURN_START, self.player.to_view())
        self.event_bus.notify(PokerEvent.TURN, self.get_snapshot())

    def discard_cards(self):
        """
            Discard all the cards not marked for hold and draws new ones.
        """

        for idx, card in enumerate(self.community_cards):
            if not card.hold:
                self.community_cards[idx] = CardState(self.deck.deal()[0], True)
        
        self.event_bus.notify(PokerEvent.CARDS_DISCARDED, self.get_snapshot())        
        self.end_hand()

    def end_hand(self):
        """Handles the end of a hand, determines hand, pays out chips, and transitions."""
        self.change_phase(PokerPhase.SHOWDOWN, self.get_snapshot())

        multiplier = 0
        hand_rank, cards = Poker.evaluate_hand([card.card for card in self.community_cards])

       # Only pairs with jacks or better pay out. Everything else pays out according to the table
        if hand_rank != HandRank.PAIR or (hand_rank == HandRank.PAIR and cards[0] >= CardRank.JACK):
            multiplier = payout_table[hand_rank]

        self.player.funds += self.bet * multiplier
        self.payout_multiplier = multiplier

        self.event_bus.notify(PokerEvent.TURN, self.get_snapshot())
        self.event_bus.notify(PokerEvent.HAND_OVER, self.get_snapshot())

        self.event_bus.notify(
            GenericEvent.TURN_START, self.player.to_view(cards_visible=True)
        )

    def finish_hand(self, reset: bool):
        if reset:
            self.event_bus.notify(PokerEvent.HAND_RESET, self.get_snapshot())
            self.start()
        else:
            self.event_bus.notify(GenericEvent.GAME_END, self.player.funds)

    @staticmethod
    def evaluate_hand(hand: list[Card]) -> tuple[HandRank, list[CardRank]]:
        """
        Evaluates a 5-card poker hand and returns a tuple containing the hand rank (e.g., pair, flush, straight)
        and a list of card ranks for tie-breaking purposes.
        The returned hand is comparable, meaning that a higher hand rank will always beat a lower one,
        and if two hands have the same rank, the tie-breaker list can be compared in order to determine the winner
        (e.g., for two pairs, the tie-breaker list would contain the ranks of the pairs and then the kicker).
        """
        # Sort ranks in descending order for easier evaluation of straights and high cards, and extract suits
        ranks = sorted([CardRank[c.rank.name] for c in hand], reverse=True)
        # The suits of all cards in the hand, used to check for flushes
        suits = [c.suit for c in hand]

        # Count the frequency of each rank in the hand, which is essential for identifying pairs, three of a kind, and four of a kind.
        counts = Counter(ranks)

        # Build a normalized 5-card comparison vector where duplicated ranks come first.
        # Examples:
        # - Pair: [pair, pair, kicker1, kicker2, kicker3]
        # - Two pair: [high_pair, high_pair, low_pair, low_pair, kicker]
        # - Trips: [trips, trips, trips, kicker1, kicker2]
        grouped_ranks = sorted(
            counts.items(), key=lambda item: (item[1], item[0]), reverse=True
        )
        score_sort = [rank for rank, freq in grouped_ranks for _ in range(freq)]

        is_flush = len(set(suits)) == 1
        is_straight = len(set(ranks)) == 5 and (max(ranks) - min(ranks) == 4)

        # Wheel Straight (A-5)
        if set(ranks) == {
            CardRank.ACE,
            CardRank.TWO,
            CardRank.THREE,
            CardRank.FOUR,
            CardRank.FIVE,
        }:
            is_straight = True
            score_sort = [
                CardRank.FIVE,
                CardRank.FOUR,
                CardRank.THREE,
                CardRank.TWO,
                CardRank.ACE,
            ]  # Ace is low in this straight

        # Return (HandRank, Tie-breaker-list)
        if is_straight and is_flush:
            return (
                (
                    HandRank.ROYAL_FLUSH
                    if score_sort[0] == CardRank.ACE
                    else HandRank.STRAIGHT_FLUSH
                ),
                score_sort,
            )

        hand_type = HandRank.HIGH_CARD

        if 4 in counts.values():
            hand_type = HandRank.FOUR_OF_A_KIND
        elif 3 in counts.values() and 2 in counts.values():
            hand_type = HandRank.FULL_HOUSE
        elif is_flush:
            hand_type = HandRank.FLUSH
        elif is_straight:
            hand_type = HandRank.STRAIGHT
        elif 3 in counts.values():
            hand_type = HandRank.THREE_OF_A_KIND
        elif list(counts.values()).count(2) == 2:
            hand_type = HandRank.TWO_PAIR
        elif 2 in counts.values():
            hand_type = HandRank.PAIR

        return (hand_type, score_sort)

    @staticmethod
    def best_hand(
        player_cards: list[Card], community_cards: list[Card]
    ) -> tuple[HandRank, list[CardRank]]:
        """
        Returns the best 5-card hand that can be made from 2 player cards and 5 community cards.

        The returned tuple is:
        - hand_score: (HandRank, tie_breaker_vector i.e. best hand) as produced by evaluate_hand
        """
        if len(player_cards) != 2:
            raise ValueError("best_hand expects exactly 2 player cards")
        if len(community_cards) != 5:
            raise ValueError("best_hand expects exactly 5 community cards")

        seven_cards = player_cards + community_cards

        best_five: list[Card] | None = None
        best_score: tuple[HandRank, list[CardRank]] | None = None

        for five_cards_tuple in combinations(seven_cards, 5):
            five_cards = list(five_cards_tuple)
            score = Poker.evaluate_hand(five_cards)

            if best_score is None or score > best_score:
                best_score = score
                best_five = five_cards

        # Guaranteed by combinations(7, 5), kept explicit for type-safety.
        if best_five is None or best_score is None:
            raise ValueError("Could not evaluate best hand")

        return best_score

    def get_available_commands(self) -> dict[PokerCommandRequest, CommandSchema]:
        no_comm_cards = len(self.community_cards) == 0

        comms = {
            PokerCommandRequest.NEW_HAND: CommandSchema(
                display_name="New Hand",
                command_class=commands.NewHandCommand,
            ) if self.game_phase == PokerPhase.SHOWDOWN else None,
            PokerCommandRequest.END_GAME: CommandSchema(
                display_name="End Game",
                    command_class=commands.EndHandCommand,
                ) if no_comm_cards or self.game_phase == PokerPhase.SHOWDOWN else None,
            PokerCommandRequest.START_ROUND: CommandSchema(
                    display_name="Start Round",
                    command_class=commands.StartRoundCommand,
            ) if len(self.community_cards) == 0 and self.bet > 0 else None,
            PokerCommandRequest.CHANGE_BET: CommandSchema(
                    display_name="Change Bet",
                    command_class=commands.ChangeBetCommand,
                    parameters=[
                        CommandParameter(
                            name="amount",
                            prompt_text="How much would you like to change your bet by? ",
                            parser=float,
                        )
                    ],
                ) if no_comm_cards else None,
            PokerCommandRequest.HOLD_CARD: CommandSchema(
                    display_name="Hold Card",
                    command_class=commands.HoldCardCommand,
                    parameters=[
                        CommandParameter(
                            name="idx",
                            prompt_text="Which card would you like to hold? (0-4) ",
                            parser=int,
                        )
                    ],
                ) if not no_comm_cards else None, # Using the len of community cards to determine if cards have been dealt, since the player should only be able to hold/discard after being dealt cards
            PokerCommandRequest.DISCARD_CARDS: CommandSchema(
                    display_name="Discard Cards",
                    command_class=commands.DiscardCardsCommand,
                ) if not no_comm_cards else None,
        }

        return {key: cmd for key, cmd in comms.items() if cmd is not None}

    def get_snapshot(self) -> PokerSnapshot:
        """Returns a snapshot of the current game state, which can be used for rendering and for AI decision-making."""
        return PokerSnapshot(
            active_player=self.active_player.to_view(),
            community_cards=[
                CardStateView(CardView.from_card(card_state.card, True), card_state.hold) for card_state in self.community_cards
            ],
            bet=self.bet,
            payout_multiplier=self.payout_multiplier,
            final_hand=self.evaluate_hand([card_state.card for card_state in self.community_cards]) if self.game_phase == PokerPhase.SHOWDOWN else None,
            available_commands=self.get_available_commands(),
        )
