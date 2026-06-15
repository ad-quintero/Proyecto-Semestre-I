from typing import TYPE_CHECKING
from unittest import case

from casino.games import Game

if TYPE_CHECKING:
    from casino.games.poker.renderer import PokerTerminalRenderer

from utils.commands.command_manager import CommandManager
from utils.commands.command_manager import CommandManager
from utils.event_listener import EventBus
from utils.cards import Deck, Card, CardView
from casino.player import PlayerAccount, PlayerController
from dataclasses import dataclass
import random
from itertools import combinations
from enum import Enum, IntEnum
from collections import Counter
from casino.games.game_manager import GameManager
from .phases import PokerPhase
from .events import PokerEvent
from . import commands
from .cpu_player import PokerCPU
from uuid import UUID, uuid4
from casino.games import Snapshot
from casino.player import PlayerBuyIn
from dataclasses import dataclass

from utils.commands.command import CommandSchema, CommandParameter
from casino.games.generic_events import GenericEvent
from casino.player import PlayerView


@dataclass
class PokerPlayer:
    id: UUID
    name: str
    cards: list[Card]
    funds: float = 0
    current_contribution: float = 0

    def to_view(self, cards_visible: bool = False) -> PokerPlayerView:
        return PokerPlayerView(
            id=self.id,
            name=self.name,
            cards=[CardView(c.rank, c.suit, cards_visible) for c in self.cards],
            funds=self.funds,
            current_contribution=self.current_contribution,
        )


@dataclass(frozen=True)
class PokerPlayerView(PlayerView):
    cards: list[CardView]
    funds: float
    current_contribution: float


@dataclass(frozen=True)
class PokerSnapshot(Snapshot):
    players_data: list[PokerPlayerView]
    """The data of all players in the game."""
    active_players: list[PokerPlayerView]
    """A list of active players, i.e. those who haven't folded."""
    active_player_id: UUID
    """The id of the current active player, i.e. the one whose turn it is."""
    player: PokerPlayerView
    """The current active player's data."""
    dealer: PokerPlayerView
    """The current dealer's data."""
    community_cards: list[CardView]
    """A list of the community cards on the table."""
    pot: float
    """The current hand's pot"""
    big_blind: float
    """The big blind amount, used to determine the small blind and the minimum raise amount. The small blind is half of the big blind."""
    current_bet: float
    """The current bet amount that players need to call to stay in the hand."""
    current_phase: PokerPhase
    """The current phase of the hand (pre-flop, flop, turn, river)."""
    available_commands: tuple[CommandSchema]
    """The list of available commands for the current active player, which can be used for rendering the UI and for AI decision-making."""
    winners: list[PokerPlayerView] | None = None


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
    cpu_players: list[PokerCPU]

    def __init__(
        self,
        game: Poker,
        player: PlayerAccount,
        renderer: PokerTerminalRenderer,
        player_buy_in: PlayerBuyIn,
        cpu_players: int = 5,
    ):
        self.event_bus = EventBus()
        self.renderer = renderer(self.event_bus)

        cpu_data = [
            PlayerBuyIn(uuid4(), f"CPU {i+1}", 1000) for i in range(cpu_players)
        ]

        self.game = game(self.event_bus, player_buy_in, cpu_data)

        self.command_manager = CommandManager(self.game)

        self.player = PlayerController(self.event_bus, self.command_manager, player.id)
        self.cpu_players = [
            PokerCPU(
                f"CPU {i+1}",
                self.command_manager,
                self.event_bus,
                cpu_data[i].player_id,
            )
            for i in range(cpu_players)
        ]


class Poker(Game):
    deck: Deck
    """The deck used in the game"""

    community_cards: list[Card]
    """The community cards on the table (the 5 cards that all players can use to make their hand)"""

    cpus: list[PokerPlayer]
    """All CPUs in the game"""

    player: PokerPlayer
    """The human player in the game"""

    active_players: list[PokerPlayer]
    """The players that are still active in the current hand (i.e. haven't folded)"""

    current_player_idx: int
    """
    The index of the current active player, i.e. the one whose turn it is. 
    This is an index into the all_players list.
    """

    dealer_idx: int
    """
    The index of the current dealer in the all_players list. Using an index makes it 
    easier to rotate the dealer each hand and to determine who pays the small and big blinds based on 
    the dealer's position.
    """

    big_blind: float
    """
    The amount of the big blind. The small blind will be half of this amount. 
    This is used to determine the initial bet amounts and the minimum raise amount.
    """

    pot: float
    """The total amount of money in the pot for the current hand."""

    current_bet: float
    """The current bet amount that players need to call to stay in the hand. This is updated as players raise."""

    last_raise: float
    """The amount of the last raise, used to calculate the minimum raise for subsequent raises in the same betting round."""

    winners: list[PokerPlayer]

    # The different phases of a poker hand, which determine the flow of the game and when community cards are revealed.
    # The game starts in the PRE_FLOP phase, then moves to FLOP, TURN, and RIVER as community cards
    # are revealed and betting rounds are completed.
    phases: list[PokerPhase] = [
        PokerPhase.PRE_FLOP,
        PokerPhase.FLOP,
        PokerPhase.TURN,
        PokerPhase.RIVER,
    ]

    current_phase_idx: int
    """The index of the current phase in the phases list, used to track the flow of the hand."""

    call_count: int
    """A counter to track how many players have called in the current betting round, used to determine when to move to the next phase."""

    def __init__(
        self, event_bus: EventBus, buy_in: PlayerBuyIn, cpu_buy_ins: list[PlayerBuyIn]
    ):
        super().__init__(event_bus, buy_in)

        self.player = PokerPlayer(
            id=buy_in.player_id, name=buy_in.name, cards=[], funds=buy_in.amount
        )
        self.cpus = [
            PokerPlayer(
                id=cpu_buy_in.player_id,
                name=cpu_buy_in.name,
                cards=[],
                funds=cpu_buy_in.amount,
            )
            for cpu_buy_in in cpu_buy_ins
        ]
        self.active_players = self.all_players
        self.winners = []

        self.deck = Deck()
        self.community_cards = []

        self.big_blind = round(buy_in.amount * 0.05, 2)
        self.pot = 0

        self.current_bet = self.big_blind
        self.last_raise = self.big_blind

        self.current_phase_idx = 0
        self.call_count = 0

        self.player_buy_in = buy_in
        self.cpu_buy_ins = cpu_buy_ins

    @property
    def all_players(self):
        """Returns a list of all players in the game, with the human player first followed by the CPUs."""
        return [self.player] + self.cpus

    @property
    def dealer(self) -> PokerPlayer:
        """Returns the current dealer."""
        return self.all_players[self.dealer_idx]

    @property
    def active_player(self) -> PokerPlayer:
        """Returns the current player."""
        return self.all_players[self.current_player_idx]

    @property
    def current_phase(self) -> PokerPhase:
        """Returns the current phase of the game."""
        return self.phases[self.current_phase_idx]

    @property
    def min_raise(self) -> float:
        """Returns the minimum raise amount based on the last raise."""
        return self.last_raise

    def start(self):
        # Reset all game state for the new hand
        self.deck = Deck()
        self.community_cards = []
        self.active_players = self.all_players
        self.pot = 0
        self.last_raise = 0
        self.big_blind = round(self.buy_in.amount * 0.05, 2)
        self.current_bet = self.big_blind
        self.current_phase_idx = 0
        self.call_count = 0
        self.winners = []

        self.change_phase(PokerPhase.CHOOSING_DEALER)
        self.choose_dealer()
        self.change_phase(PokerPhase.DEALING_CARDS)
        self.deal_cards()
        self.pay_blinds()
        self.change_phase(PokerPhase.PRE_FLOP, self.get_snapshot())
        self.advance_turn()

    def end(self):
        pass

    def choose_dealer(self):
        """Randomly selects a dealer from all players (including the human player)."""

        self.change_phase(PokerPhase.CHOOSING_DEALER)
        self.dealer_idx = random.randint(0, len(self.all_players) - 1)
        self.current_player_idx = (self.dealer_idx + 3) % len(
            self.active_players
        )  # The player to the left of the big blind starts first, which is three positions to the left of the dealer.

        self.event_bus.notify(
            PokerEvent.CHOOSE_DEALER,
            self.get_snapshot(),
        )

    def deal_cards(self):
        """Deals 2 cards to each player from the deck."""

        self.change_phase(PokerPhase.DEALING_CARDS)

        for player in self.all_players:
            player.cards = self.deck.deal(2)

        self.event_bus.notify(PokerEvent.DEAL_CARDS, self.get_snapshot())

    def pay_blinds(self):
        """Handles the payment of the small and big blinds at the start of each hand."""
        small_blind_idx = (self.dealer_idx + 1) % len(self.active_players)
        big_blind_idx = (self.dealer_idx + 2) % len(self.active_players)

        small_blind_amount = self.big_blind / 2
        big_blind_amount = self.big_blind

        # Small blind payment
        self.all_players[small_blind_idx].funds -= small_blind_amount
        self.all_players[small_blind_idx].current_contribution = small_blind_amount
        self.pot += small_blind_amount

        # Big blind payment
        self.all_players[big_blind_idx].funds -= big_blind_amount
        self.all_players[big_blind_idx].current_contribution = big_blind_amount
        self.pot += big_blind_amount

        self.event_bus.notify(PokerEvent.PAID_BLIND, self.get_snapshot())

    def advance_turn(self):
        """Advances the turn to the next player."""

        # 1. Check if we need to advance the phase
        if (
            self.call_count >= len(self.active_players)
            or all(player.funds == 0 for player in self.active_players)
            or len(self.active_players) == 1
        ):
            hand_ended = self.next_phase()
            if hand_ended:
                # BREAK THE LOOP! The hand is over, no one else gets a turn.
                return
        else:
            # 2. Only advance the index +1 if we are staying in the SAME betting round
            self.current_player_idx = (self.current_player_idx + 1) % len(
                self.all_players
            )
            while self.all_players[self.current_player_idx] not in self.active_players:
                self.current_player_idx = (self.current_player_idx + 1) % len(
                    self.all_players
                )

        target_player = self.active_player

        # 3. Proceed with handing over the turn
        self.event_bus.notify(PokerEvent.CHANGE_PLAYER_TURN, self.get_snapshot())
        self.event_bus.notify(
            GenericEvent.TURN_START, self.active_player.to_view(cards_visible=True)
        )
        if target_player.id == self.player.id:
            self.event_bus.notify(
                PokerEvent.AVAILABLE_COMMANDS,
                self.get_snapshot(),
            )

    def next_phase(self) -> bool:
        """Advances the game to the next phase. Returns True if the hand ended, False otherwise."""
        if (
            self.current_phase == PokerPhase.RIVER
            or len(self.active_players) == 1
            or all(player.funds == 0 for player in self.active_players)
        ):
            self.end_hand()
            return True  # 🛑 Tell advance_turn to STOP

        self.current_phase_idx += 1
        self.call_count = 0

        # Deal the corresponding community cards of each phase

        match self.current_phase:
            case PokerPhase.FLOP:
                self.community_cards += self.deck.deal(3)
            case PokerPhase.TURN | PokerPhase.RIVER:
                self.community_cards += self.deck.deal(1)

        for player in self.active_players:
            player.current_contribution = 0

        # 1. Start looking at the player immediately to the left of the dealer
        search_idx = (self.dealer_idx + 1) % len(self.all_players)

        # 2. Keep moving left until we find a player who is still active
        while self.all_players[search_idx] not in self.active_players:
            search_idx = (search_idx + 1) % len(self.all_players)

        # 3. Assign the turn to the first active player found
        self.current_player_idx = search_idx

        self.change_phase(self.current_phase, self.get_snapshot())
        return False  # 🟢 Tell advance_turn it is safe to proceed

    def player_call(self):
        """Handles the active player calling the current bet, including updating the pot and the player's money."""
        payment = (
            min(self.current_bet, self.active_player.funds)
            - self.active_player.current_contribution
        )

        self.pot += payment
        self.active_player.funds -= payment

        # Only count as a call if the player is actually calling the current bet,
        # and not just going all-in with a smaller amount
        if payment == self.current_bet:
            self.call_count += 1
            self.event_bus.notify(PokerEvent.PLAYER_CALL, self.get_snapshot())
        else:
            self.event_bus.notify(PokerEvent.PLAYER_ALL_IN, self.get_snapshot())

        self.advance_turn()

    def player_raise(self, new_bet: float):
        """
        Raises the bet to new_bet by the active player.
        """

        # 1. Calculate how much the player must pay
        # (new_bet is the total)
        amount_to_add = new_bet - self.active_player.current_contribution

        # 2. Does the player have enough money?
        if amount_to_add > self.active_player.funds:
            raise ValueError("Not enought funds to raise to that amount")

        # 3. Minimum required:
        # The raise is the part that exceeds the current bet.
        raise_amount = new_bet - self.current_bet

        # If not all in it must be at least the minimum raise, but if it's an all-in it can be less than the minimum raise as long as it's more than the current bet.
        is_all_in = amount_to_add == self.active_player.funds

        if not is_all_in:
            if new_bet < self.current_bet + self.min_raise:
                raise ValueError(
                    f"The minimum raise is to {self.current_bet + self.min_raise}"
                )

        # 4. Execution of the move
        self.active_player.funds -= amount_to_add
        self.pot += amount_to_add
        self.active_player.current_contribution = new_bet

        # Update the last raise amount if this raise is bigger than the previous one, which will affect the minimum raise for the next raises in the same betting round.
        if raise_amount > self.min_raise:
            self.raise_bet(new_bet)

        self.advance_turn()

    def raise_bet(self, new_bet: float):
        """
        Raises the game's bet to the new bet amount, and updates the last raise amount accordingly.
        This method should be called whenever a player raises, to ensure that the minimum raise amount is correctly calculated for
        subsequent raises.
        """
        self.last_raise = new_bet - self.current_bet
        self.current_bet = new_bet

    def player_fold(self):
        """Handles the active player folding, which removes them from the active players in the current hand."""
        self.active_players.remove(self.active_player)
        self.event_bus.notify(PokerEvent.PLAYER_FOLD, self.get_snapshot())

        self.advance_turn()

    def end_hand(self):
        """Handles the end of a hand, determines winners, distributes chips, and transitions."""
        self.change_phase(PokerPhase.SHOWDOWN, self.get_snapshot(True))

        # 1. Determine the winner(s)
        if len(self.active_players) == 1:
            # Everyone else folded, lone survivor takes the pot
            winners = [self.active_players[0].id]
        else:
            # Showdown! Evaluate best 5-card hands
            # (You'll map players to their best_hand score and find the max)
            player_scores = {
                player.id: self.best_hand(player.cards, self.community_cards)
                for player in self.active_players
            }
            max_score = max(player_scores.values())
            self.winners = [
                self.all_players[i]
                for i, (_player_id, score) in enumerate(player_scores.items())
                if score == max_score
            ]

        # 2. Distribute the pot (handle split pots smoothly)
        share = self.pot / len(self.winners)
        for winner in self.winners:
            for player in self.all_players:
                if player.id == winner:
                    player.funds += share
                    break

        # 3. Notify the event bus so the renderer can show who won!
        # You'll want to add a custom event like PokerEvent.HAND_OVER
        # and pass the winners/pot data to your renderer
        self.event_bus.notify(
            PokerEvent.HAND_OVER,
            self.get_snapshot(True),
        )

        # 4. Check if the game is completely over
        if self.player.funds <= 0:
            self.end()  # Call the base class end() method to set game_active = False
            return

        # Set the current player to be the one just before the human player,
        # so that when we call advance_turn() it will move to the human player and prompt for a new hand or end game.
        self.current_player_idx = self.all_players.index(self.player)

        self.event_bus.notify(PokerEvent.AVAILABLE_COMMANDS, self.get_snapshot(True))
        self.event_bus.notify(
            GenericEvent.TURN_START, self.player.to_view(cards_visible=True)
        )

    def finish_hand(self, reset: bool):
        if reset:
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

    def get_available_commands(self) -> tuple[CommandSchema]:
        if self.game_phase == PokerPhase.SHOWDOWN:
            return (
                CommandSchema(
                    display_name="New Hand",
                    command_class=commands.ResetHandCOmmand,
                ),
                CommandSchema(
                    display_name="End Game",
                    command_class=commands.EndHandCommand,
                ),
            )
        else:
            return (
                CommandSchema(
                    display_name="Call",
                    command_class=commands.CallCommand,
                ),
                CommandSchema(
                    display_name="Raise",
                    command_class=commands.RaiseCommand,
                    parameters=[
                        CommandParameter(
                            name="amount",
                            prompt_text="How much would you like to raise to? ",
                            parser=float,
                        )
                    ],
                ),
                CommandSchema(
                    display_name="Fold",
                    command_class=commands.FoldCommand,
                ),
            )

    def get_snapshot(self, show_cpu_cards: bool = False) -> PokerSnapshot:
        """Returns a snapshot of the current game state, which can be used for rendering and for AI decision-making."""
        return PokerSnapshot(
            players_data=[
                p.to_view(cards_visible=p.id == self.player.id or show_cpu_cards)
                for p in self.all_players
            ],
            active_player=self.active_player.to_view(self.active_player.id == self.player.id or show_cpu_cards),
            active_players=[p.to_view(p.id == self.player.id or show_cpu_cards) for p in self.active_players],
            active_player_id=self.active_player.id,
            player=self.active_player.to_view(),
            dealer=self.dealer.to_view(),
            community_cards=[
                CardView(c.rank, c.suit, True) for c in self.community_cards
            ],
            pot=self.pot,
            big_blind=self.big_blind,
            current_bet=self.current_bet,
            current_phase=self.current_phase,
            available_commands=self.get_available_commands(),
            winners=[p.to_view() for p in self.winners] if self.winners else None,
        )
