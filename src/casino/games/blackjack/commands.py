from casino.games.blackjack import BlackjackPhase
from utils.commands.command import Command
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .blackjack import Blackjack

class PlaceBetCommand(Command):
    """Command to handle the player's bet placement."""

    game: Blackjack
    amount: int

    def __init__(self, game: Blackjack, amount: int):
        self.game = game
        self.amount = amount

    def execute(self):
        self.game.place_bet(self.amount)

class RemoveBetCommand(Command):
    """Command to handle the player's bet removal (if they change their mind before the round starts)."""

    game: Blackjack

    def __init__(self, game: Blackjack, amount: int):
        self.game = game
        self.amount = amount

    def execute(self):
        self.game.remove_bet(self.amount)

class StartRoundCommand(Command):
    """Command to start the round after placing bets."""

    game: Blackjack

    def __init__(self, game: Blackjack):
        self.game = game

    def execute(self):
        self.game.start_round()

class HitCommand(Command):
    """Command to handle the player's decision to hit (take another card)."""

    game: Blackjack

    def execute(self):
        # If the active player is None, it means it's the dealer's turn, so we use the dealer as the active player for hitting.
        active_player = self.game.player if self.game.game_phase == BlackjackPhase.PLAYER_TURN else self.game.dealer
        self.game.hit(active_player)

class StandCommand(Command):
    """Command to handle the player's decision to stand (keep their current hand)."""

    game: Blackjack

    def execute(self):
        self.game.dealer_play()

class ResetCommand(Command):
    """Command to reset the game state for a new round."""

    game: Blackjack

    def execute(self):
        self.game.reset_game()

class EndCommand(Command):
    """Command to end the current round and reset the game state for a new round."""

    game: Blackjack

    def execute(self):
        self.game.end_game()
