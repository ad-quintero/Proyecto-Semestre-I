from utils.commands.command import Command
from casino.games.roulette.bets import RouletteBet

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from casino.games.roulette.roulette import Roulette

class PlaceBetCommand(Command):
    """Command to place a bet on the roulette table."""
    bet: RouletteBet
    game: Roulette

    def __init__(self, game: Roulette, bet: RouletteBet):
        self.bet = bet
        self.game = game

    def execute(self):
        """Executes the command to place a bet."""
        # Validate the bet parameters before placing it
        self.bet.validate()

        self.game.place_bet(self.bet)

class RemoveBetCommand(Command):
    """Command to remove a bet from the roulette table."""
    bet:  RouletteBet
    game: Roulette

    def __init__(self, game: Roulette, bet: RouletteBet):
        self.bet = bet
        self.game = game

    def execute(self):
        """Executes the command to remove a bet."""
        self.game.remove_bet(self.bet)

class SpinWheelCommand(Command):
    """Command to spin the roulette wheel."""
    game: Roulette

    def __init__(self, game: Roulette):
        self.game = game

    def execute(self):
        """Executes the command to spin the wheel."""
        self.game.spin_wheel()
    
class ClearBetsCommand(Command):
    """Command to clear all bets from the roulette table."""
    game: Roulette

    def __init__(self, game: Roulette):
        self.game = game

    def execute(self):
        """Executes the command to clear all bets."""
        self.game.clear_bets()

class EndRoundCommand(Command):
    """Command to end the current round and calculate payouts."""
    game: Roulette

    def __init__(self, game: Roulette):
        self.game = game

    def execute(self):
        """Executes the command to end the round."""
        self.game.end_round()
