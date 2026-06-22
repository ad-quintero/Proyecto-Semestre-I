from typing import Optional, TYPE_CHECKING
from uuid import UUID

from utils.commands.command import CommandSchema, CommandParameter
from utils.event_listener import EventBus

from . import BlackjackPhase, BlackJackCommandRequest
from casino.games import Game
from casino.player import PlayerAccount, PlayerBuyIn, PlayerController, PlayerView

if TYPE_CHECKING:
    from casino.games.blackjack.renderer import BlackjackRenderer

from utils.cards import CardView, Deck, Card, Rank
from dataclasses import dataclass, field
from casino.games.game_manager import GameManager
from .commands import HitCommand, StandCommand
from casino.games.generic_events import GenericEvent
from . import BlackjackEvent
from casino.games import Snapshot
from .player_controller import BlackjackPlayerController

from . import commands


@dataclass(frozen=True)
class BlackjackSnapshot(Snapshot):
    """
    A snapshot of the current state of the Blackjack game, used for rendering and game logic.
    It includes information about the player's hand, the dealer's hand, the current bet, and the game phase.
    """
    active_player: BlackjackPlayerView
    """The currently active player in the game (either the player or the dealer). This can be used to determine whose turn it is and how to render the game state accordingly."""
    player_cards: list[CardView]
    """A list of CardView objects representing the player's current hand of cards. This can be used to display the player's hand in the UI."""
    dealer_cards: list[CardView]
    """A list of CardView objects representing the dealer's current hand of cards. This can be used to display the dealer's hand in the UI."""
    bet: float
    """The current bet amount placed by the player. This can be used to display the bet in the UI and calculate payouts."""
    game_phase: BlackjackPhase
    """
    The current phase of the game (e.g., WAITING_FOR_BET, PLAYER_TURN, DEALER_TURN, ROUND_END). 
    This can be used to determine which actions are available to the player and how to render the game state.
    """
    available_commands: dict[BlackJackCommandRequest, CommandSchema] = field(default_factory=dict)
    """A set of CommandSchema objects representing the commands available to the player in the current game state."""
    payout: float = None
    """The amount won or lost (positive for win, negative for loss, zero for tie)"""


@dataclass
class BlackJackPlayer:
    """
    Represents a player in the Blackjack game, holding their hand of cards and providing
    methods to calculate hand value and check for blackjack or bust conditions.
    """

    player_id: UUID
    balance: int
    cards: list[Card] = field(default_factory=list)

    @property
    def hand_value(self) -> int:
        """Calculate the total value of the player's hand, accounting for Aces."""
        value = 0
        aces = 0

        for card in self.cards:
            if card.rank in [Rank.JACK, Rank.QUEEN, Rank.KING]:
                value += 10
            elif card.rank == Rank.ACE:
                aces += 1
                value += 11
            else:
                value += int(card.rank.value)

        while value > 21 and aces > 0:
            value -= 10
            aces -= 1

        return value

    def to_view(self, cards_visible: bool = True) -> BlackjackPlayerView:
        """Converts the player's state to a view object for rendering and AI decision-making."""
        return BlackjackPlayerView(
            id=self.player_id,
            name="Player" if self.player_id else "Dealer",
            cards=[
                CardView.from_card(card, face_up=cards_visible) for card in self.cards
            ],
            balance=self.balance,
        )

    @property
    def is_blackjack(self) -> bool:
        """Check if the player's hand is a blackjack (an Ace and a 10-value card)."""
        return len(self.cards) == 2 and self.hand_value == 21

    @property
    def has_busted(self) -> bool:
        """Check if the player's hand value exceeds 21 (busted)."""
        return self.hand_value > 21


@dataclass(frozen=True)
class BlackjackPlayerView(PlayerView):
    """A view of the player's state in the Blackjack game, used for rendering and AI decision-making."""

    cards: list[CardView]
    balance: int

class BlackjackManager(GameManager):
    """
    Manages the state and flow of the Blackjack game, including handling player actions and game logic.
    This class is responsible for processing commands from the player, updating the game state, and emitting events for rendering and interaction.
    """

    def __init__(self, game: Blackjack, player: PlayerAccount, renderer: BlackjackRenderer, player_buyin: PlayerBuyIn):
        super().__init__(game, player, renderer, player_buyin)

        self.player_controller = BlackjackPlayerController(self.event_bus, self.command_manager, player.id)

class Blackjack(Game):
    """
    Represents the Blackjack game, managing the flow of the game and handling player actions.
        The game progresses through several phases:
        - WAITING_FOR_BET: The game is waiting for the player to place a bet.
        - PLAYER_TURN: The player can choose to hit or stand.
        - DEALER_TURN: The dealer plays according to standard Blackjack rules.
        - ROUND_END: The round has ended, and the outcome is determined.

        Events are emitted at key points in the game, such as when a player hits, when the dealer hits,
        and when the game ends, allowing for flexible rendering and interaction.
    """

    deck: Deck
    dealer: BlackJackPlayer
    player: BlackJackPlayer
    bet: float
    game_phase: BlackjackPhase

    def __init__(self, event_bus: EventBus, buyin: PlayerBuyIn):
        super().__init__(event_bus, buyin)
        self.dealer = BlackJackPlayer(None, 0, [])
        self.player = BlackJackPlayer(buyin.player_id, buyin.amount, [])
        self.deck = Deck(True)
        self.bet = buyin.amount
        self.game_phase = BlackjackPhase.PLAYER_TURN

        self.bet: int = 0

    @property
    def active_player(self) -> Optional[BlackJackPlayer]:
        """
        Returns the currently active player.
        """
        return self.player
    
    def start(self):
        self.event_bus.notify(GenericEvent.TURN_START, self.player.to_view())
        self.change_phase(BlackjackPhase.PLAYER_TURN, self.get_snapshot())


    def place_bet(self, amount: int):
        """Handles the player's bet placement, ensuring it is valid and updating the game state accordingly."""
        if amount <= 0:
            raise ValueError("Bet amount must be greater than zero.")
        
        if amount > self.player.balance:
            raise ValueError("Bet amount cannot exceed player's current balance.")

        self.bet += amount
        self.player.balance -= amount

        self.event_bus.notify(BlackjackEvent.PLACE_BET, self.get_snapshot())
        self.event_bus.notify(GenericEvent.PHASE_CHANGE, (BlackjackPhase.PLAYER_TURN, self.get_snapshot()))

    def remove_bet(self, amount: int):
        """Handles the player's bet removal, allowing them to adjust their bet before the round starts."""
        if amount <= 0:
            raise ValueError("Amount to remove must be greater than zero.")
        
        if amount > self.bet:
            raise ValueError("Amount to remove cannot exceed the current bet.")

        self.bet -= amount
        self.player.balance += amount

        self.event_bus.notify(BlackjackEvent.REMOVE_BET, self.get_snapshot())
        self.event_bus.notify(GenericEvent.PHASE_CHANGE, (BlackjackPhase.PLAYER_TURN, self.get_snapshot()))

    def start_round(self):
        # Give initial cards to player and dealer
        for _ in range(2):
            self.change_phase(BlackjackPhase.PLAYER_TURN, self.get_snapshot())
            self.hit(self.player)

            self.change_phase(BlackjackPhase.DEALER_TURN, self.get_snapshot())
            self.hit(self.dealer)

        self.event_bus.notify(
            GenericEvent.TURN_START, self.player.to_view(cards_visible=True)
        )
        self.change_phase(BlackjackPhase.PLAYER_TURN, self.get_snapshot())

        # If the dealer has a blackjack, the round ends immediately
        if self.dealer.is_blackjack:
            self.end_round()

    def hit(self, player: BlackJackPlayer):
        """Deals a new card to the specified player."""
        new_card = self.deck.deal(1)[0]
        player.cards.append(new_card)

        player_turn = self.player == player

        self.event_bus.notify(
            (BlackjackEvent.PLAYER_HIT if player_turn else BlackjackEvent.DEALER_HIT),
            self.get_snapshot(),
        )

        if player.hand_value > 21 or player.is_blackjack:
            self.end_round()
        else:
            self.change_phase(
                (
                    BlackjackPhase.PLAYER_TURN
                    if player_turn
                    else BlackjackPhase.DEALER_TURN
                ),
                self.get_snapshot(),
            )

    def dealer_play(self):
        self.change_phase(BlackjackPhase.DEALER_TURN, self.get_snapshot())

        while self.dealer.hand_value < 17:
            self.hit(self.dealer)

        # Finish the round after the dealer has completed their turn
        self.end_round()

    def end_round(self):
        self.change_phase(BlackjackPhase.ROUND_END, self.get_snapshot())

        payout = 0
        event = None

        if self.player.has_busted or (
            not self.dealer.has_busted
            and self.dealer.hand_value > self.player.hand_value
        ):
            event = BlackjackEvent.DEALER_WINS
            # Player loses, so we return a negative payout to indicate loss
            payout = -self.bet
        elif self.dealer.has_busted or self.player.hand_value > self.dealer.hand_value:
            event = BlackjackEvent.PLAYER_WINS

            # Player wins, so we pay out the bet (return the original bet plus winnings)
            if self.player.is_blackjack:
                payout = self.bet * 2.5  # Blackjack pays 3:2
            else:
                payout = self.bet * 2  # Regular win pays 1:1
        else:
            # It's a tie, so we return the player's original bet
            event = BlackjackEvent.TIE
            payout = self.bet

        final_snapshot = self.get_snapshot(True, payout=payout)

        self.event_bus.notify(event, final_snapshot)
        self.event_bus.notify(GenericEvent.GAME_END, payout)

    def get_available_commands(self) -> dict[BlackJackCommandRequest, CommandSchema]:
        comms = {
            BlackJackCommandRequest.PLACE_BET: CommandSchema("Place Bet", commands.PlaceBetCommand, parameters=[CommandParameter(name="amount", prompt_text="Enter bet amount:", parser=int)]) if self.game_phase == BlackjackPhase.PLAYER_TURN and not self.player.cards else None,
            BlackJackCommandRequest.REMOVE_BET: CommandSchema("Remove Bet", commands.RemoveBetCommand, parameters=[CommandParameter(name="amount", prompt_text="Enter amount to remove:", parser=int)]) if self.game_phase == BlackjackPhase.PLAYER_TURN and not self.player.cards else None,
            BlackJackCommandRequest.START_ROUND: CommandSchema("Start Round", commands.StartRoundCommand) if self.bet > 0 and not self.player.cards else None,
            BlackJackCommandRequest.HIT: CommandSchema("Hit", commands.HitCommand) if self.game_phase == BlackjackPhase.PLAYER_TURN and self.player.cards else None,
            BlackJackCommandRequest.STAND: CommandSchema("Stand", commands.StandCommand) if self.game_phase == BlackjackPhase.PLAYER_TURN and self.player.cards else None,
        }
        return {
            cmd: schema for cmd, schema in comms.items() if schema
        }

    def get_snapshot(
        self, show_dealer_cards: bool = False, **kwargs
    ) -> BlackjackSnapshot:
        """Returns a snapshot of the current game state for rendering and logic purposes."""
        return BlackjackSnapshot(
            self.active_player.to_view(),
            [CardView.from_card(card) for card in self.player.cards],
            [
                CardView.from_card(card, face_up=i == 0 or show_dealer_cards)
                for i, card in enumerate(self.dealer.cards)
            ],
            self.bet,
            self.game_phase,
            self.get_available_commands(),
            **kwargs
        )
