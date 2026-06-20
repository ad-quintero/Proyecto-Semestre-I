from utils.commands.command import Command
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .poker import Poker

class PlaceBetCommand(Command):
    game: Poker

    def __init__(self, game: Poker, amount: float):
        super().__init__(game)
        self.amount = amount

    def execute(self):
        self.game.place_bet(self.amount)


class RemoveBetCommand(Command):
    game: Poker

    def __init__(self, game: Poker, amount: float):
        super().__init__(game)
        self.amount = amount

    def execute(self):
        self.game.remove_bet(self.amount)

class StartRoundCommand(Command):
    game: Poker

    def __init__(self, game: Poker):
        super().__init__(game)

    def execute(self):
        self.game.start_round()

class HoldCardCommand(Command):
    game: Poker

    def __init__(self, game: Poker, idx: int):
        super().__init__(game)
        
        if idx > 4:
            raise IndexError("Card index must be between 0 and 4.")
        self.idx = idx

    def execute(self):
        self.game.hold_card(self.idx)

class DiscardCardsCommand(Command):
    game: Poker

    def __init__(self, game: Poker):
        super().__init__(game)


    def execute(self):
        self.game.discard_cards()

class NewHandCommand(Command):
    game: Poker

    def __init__(self, game: Poker):
        super().__init__(game)

    def execute(self):
        self.game.finish_hand(reset=True)

class EndHandCommand(Command):
    game: Poker

    def __init__(self, game: Poker):
        super().__init__(game)

    def execute(self):
        self.game.finish_hand(reset=False)
