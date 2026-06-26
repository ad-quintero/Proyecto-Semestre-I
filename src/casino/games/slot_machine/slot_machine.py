from dataclasses import dataclass
from uuid import UUID

from casino.games import Game
from casino.games.game_manager import GameManager
from casino.games.slot_machine.events import SlotMachineCommandRequest, SlotMachineEvents
from casino.games.slot_machine.player_controller import SlotMachinePlayerController
from utils import renderer
from utils.event_listener import EventBus
from casino.player import PlayerAccount, PlayerBuyIn
from utils.commands.command import CommandSchema, CommandParameter
from . import commands
from casino.games import Snapshot
from casino.games.generic_events import GenericEvent
from casino.player import PlayerView

from enum import Enum
import random

@dataclass
class SlotMachinePlayer:
    id: UUID
    name: str
    funds: float = 0

    def to_view(self) -> SlotMachinePlayerView:
        return SlotMachinePlayerView(id=self.id, name=self.name, funds=self.funds)


@dataclass(frozen=True)
class SlotMachinePlayerView(PlayerView):
    funds: float

class Reels(Enum):
    CHERRY = "🍒"
    LEMON = "🍋"
    BELL = "🔔"
    JACKPOT = "💰"


class SlotMachineManager(GameManager):
    def __init__(
        self,
        game: SlotMachine,
        player: PlayerAccount,
        renderer: renderer.Renderer,
        buyin: PlayerBuyIn,
    ):
        super().__init__(game, player, renderer, buyin)
        self.player_controller = SlotMachinePlayerController(self.event_bus, self.command_manager, buyin.player_id)


@dataclass(frozen=True)
class SlotMachineSnapshot(Snapshot):
    """A snapshot of the current state of the Slot Machine game, used for rendering and game logic."""

    active_player: SlotMachinePlayerView
    """Information about the active player, including their name and current funds. This can be used to display the player's status in the UI."""
    reels: tuple[Reels]
    """A list of strings representing the current symbols on the slot machine reels. This can be used to display the reels in the UI."""
    bet: float
    """The current bet amount placed by the player. This can be used to display the bet in the UI and calculate payouts."""
    multiplier: float
    """The multiplier of the last spin."""
    available_commands: dict[SlotMachineCommandRequest, CommandSchema]


class SlotMachine(Game):
    """A class representing a slot machine game, which inherits from the base Game class."""

    odds = {
        Reels.CHERRY: 0.4,
        Reels.LEMON: 0.3,
        Reels.BELL: 0.2,
        Reels.JACKPOT: 0.1,
    }

    paytable = {
        (Reels.JACKPOT, Reels.JACKPOT, Reels.JACKPOT): 100,
        (Reels.CHERRY, Reels.CHERRY, Reels.CHERRY): 10,
        (Reels.LEMON, Reels.LEMON, Reels.LEMON): 20,
        (Reels.BELL, Reels.BELL, Reels.BELL): 50,
    }
    """A paytable defining the payout for specific combinations of symbols on the reels. This can be used to calculate winnings based on the current state of the reels."""

    outcome: tuple[Reels]
    """The outcome of the most recent spin, represented as a list of Reels. This can be used to determine winnings and display the result of the spin in the UI."""

    bet: float
    """The current bet amount placed by the player. This can be used to calculate winnings and display the bet in the UI."""

    def __init__(self, event_bus: EventBus, buy_in: PlayerBuyIn):
        super().__init__(event_bus, buy_in)
        self.bet = 0
        self.game_multiplier = 1.0
        self.outcome = ()
        self.multiplier = 0

        self.player = SlotMachinePlayer(id=buy_in.player_id, name=buy_in.name, funds=buy_in.amount)

    def start(self):
        self.event_bus.notify(
            GenericEvent.TURN_START,
            self.player.to_view(),
        )
        self.event_bus.notify(SlotMachineEvents.PLAYER_CHOICE, self.get_snapshot())

    def change_bet(self, amount: float):
        # Calculate what the new bet *would* be
        proposed_bet = self.bet + amount
    
        # 🎯 RULE 1: The bet cannot drop below 0
        # 🎯 RULE 2: The bet cannot exceed the player's current total cash
        if 0 <= proposed_bet <= self.player.funds:
            self.bet = proposed_bet

            self.event_bus.notify(SlotMachineEvents.BET_CHANGE, self.get_snapshot())

            self.event_bus.notify(
                GenericEvent.TURN_START,
                self.player.to_view(),
            )
            self.event_bus.notify(SlotMachineEvents.PLAYER_CHOICE, self.get_snapshot())
        else:
            raise ValueError(f"Invalid bet change: {amount}. Proposed bet would be {proposed_bet}, but player funds are {self.player.funds}.")

    def spin(self):
        self.player.funds -= self.bet
        self.event_bus.notify(SlotMachineEvents.SPIN_START, self.get_snapshot())

        self.outcome = tuple(random.choices(
            population=list(self.odds.keys()), weights=list(self.odds.values()), k=3
        ))

        self.multiplier = self.paytable.get(self.outcome, 0)
        payout = self.multiplier * self.bet * self.game_multiplier

        self.player.funds += payout

        self.event_bus.notify(SlotMachineEvents.SPIN_RESULT, self.get_snapshot())

        self.event_bus.notify(
            GenericEvent.TURN_START,
            self.player.to_view(),
        )
        self.event_bus.notify(SlotMachineEvents.PLAYER_CHOICE, self.get_snapshot())

    def end(self):
        self.event_bus.notify(GenericEvent.GAME_END, self.player.funds)

    def get_snapshot(self) -> SlotMachineSnapshot:
        return SlotMachineSnapshot(
            active_player=self.player.to_view(),
            reels=self.outcome,
            bet=self.bet,
            multiplier=self.multiplier,
            available_commands=self.get_available_commands()
        )

    def get_available_commands(self) -> dict[SlotMachineCommandRequest, CommandSchema]:
        comms = {
                SlotMachineCommandRequest.SPIN: CommandSchema("Spin", commands.SpinCommand) if self.bet and self.player.funds > self.bet else None,
                SlotMachineCommandRequest.CHANGE_BET: CommandSchema(
                    "Change Bet",
                    commands.ChangeBetCommand,
                    parameters=[
                        CommandParameter(
                            "new_bet", prompt_text="Enter new bet amount: ", parser=float
                        )
                    ],
                ),
                SlotMachineCommandRequest.END_GAME: CommandSchema("End Game", commands.EndCommand)
        }

        return {cmd: schema for cmd, schema in comms.items() if schema is not None}
