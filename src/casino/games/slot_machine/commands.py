from utils.commands.command import Command
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from casino.games.slot_machine.slot_machine import SlotMachine


class SpinCommand(Command):
    game: SlotMachine

    def __init__(self, game: SlotMachine):
        self.game = game

    def execute(self):
        self.game.spin()

class ChangeBetCommand(Command):
    game: SlotMachine

    def __init__(self, game: SlotMachine, new_bet: float):
        self.game = game
        self.new_bet = new_bet

    def execute(self):
        self.game.change_bet(self.new_bet)

class EndCommand(Command):
    game: SlotMachine

    def __init__(self, game: SlotMachine):
        self.game = game
        self.description = "(E) End the game"

    def execute(self):
        self.game.end()
