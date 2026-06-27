import uuid

from casino.games.blackjack.renderer import BlackjackRenderer, BlackjackTerminalRenderer
from casino.player import PlayerAccount
from casino.games.blackjack.blackjack import Blackjack, BlackjackManager
from casino.games.poker.poker import Poker, PokerManager
from casino.games.poker.renderer import PokerRenderer
from casino.games.game_manager import GameManager
from casino.games import Game
from dataclasses import dataclass
from utils.renderer import Renderer
from .games.generic_events import GenericEvent
from utils.commands.command_manager import CommandManager
from typing import Type, Literal
from casino.games.slot_machine.slot_machine import (
    SlotMachine,
    SlotMachineManager,
)
from casino.games.slot_machine.renderer import SlotMachineRenderer
from casino.games.roulette.roulette import Roulette, RouletteManager
from casino.games.roulette.renderer import RouletteTerminalRenderer
from casino.renderer import CasinoRenderer

from nicegui import ui

@dataclass
class CasinoGame:
    name: str
    game: Type[Game]
    manager: Type[GameManager]
    renderer: Type[Renderer]


class Casino:
    """
    A class representing a casino, which can have multiple players.
    """

    name: str
    player: PlayerAccount
    games: list[CasinoGame]
    game_active: bool

    def __init__(self, name: str):
        self.name = name
        self.game_active = False
        self.active_game_manager: GameManager | None = None

        self.games = [
            CasinoGame(
                name="Blackjack",
                game=Blackjack,
                manager=BlackjackManager,
                renderer=BlackjackRenderer,
            ),
            CasinoGame(
                name="Poker", game=Poker, manager=PokerManager, renderer=PokerRenderer
            ),
            CasinoGame(
                name="Slot Machine",
                game=SlotMachine,
                manager=SlotMachineManager,
                renderer=SlotMachineRenderer,
            ),
            CasinoGame(
                name="Roulette",
                game=Roulette,
                manager=RouletteManager,
                renderer=RouletteTerminalRenderer,
            )
        ]

        self.active_page: CasinoRenderer = CasinoRenderer(on_game_selected=self.on_game_selected)
        self.player = PlayerAccount(id=uuid.uuid4(), name="Player1", balance=1000)

    def on_game_selected(self, game_name: Literal["Blackjack", "Poker", "Slot Machine", "Roulette"]):
        selected_game = next((game for game in self.games if game.name == game_name), None)
        if selected_game:
            self.active_game_manager = selected_game.manager(
                selected_game.game,
                self.player,
                selected_game.renderer,
                self.player.buy_in(self.player.balance),
            )
            self.active_game_manager.event_bus.subscribe(GenericEvent.GAME_END, self.end_game)
            self.active_page.build_ui(game_to_render=self.active_game_manager.renderer)
            self.active_game_manager.game.start()

    @ui.refreshable_method
    async def menu(self):
        self.active_page.build_ui()
        # while True:
        #     print(f"Welcome to {self.name}!")
        #     print("Please select a game:")
        #     for idx, game in enumerate(self.games, start=1):
        #         print(f"{idx}. {game.name}")
        #     print("0. Exit")

        #     choice = input("Enter your choice: ")
        #     if choice == "0":
        #         print("Thank you for visiting the casino! Goodbye!")
        #         break

        #     try:
        #         selected_game = self.games[int(choice) - 1]

        #         # The actual instances of the games are created here, after the player has made their choice.
        #         # This allows us to subscribe to game events before the game loop starts.
        #         manager = selected_game.manager(
        #             selected_game.game,
        #             self.player,
        #             selected_game.renderer,
        #             self.player.buy_in(100),
        #         )  # Example buy-in amount

        #         manager.event_bus.subscribe(GenericEvent.GAME_END, self.end_game)

        #         # Run game setup code before accepting player input
        #         manager.game.start()

        #         self.game_active = True
        #         while self.game_active:
        #             if manager.player.is_my_turn:
        #                 choice = input("\nSelect an option: ")

        #                 try:
        #                     choice = int(choice) - 1
        #                     command = manager.command_manager.get_commands()[choice]

        #                     if command.parameters:
        #                         for param in command.parameters:
        #                             user_input = input(param.prompt_text)
        #                             param.set_value(user_input)

        #                     if command:
        #                         manager.command_manager.execute_command(command)
        #                 except (IndexError, ValueError) as e:
        #                     print(e)
        #                     print(
        #                         "Invalid input. Please enter a number corresponding to the available options."
        #                     )
        #     except (IndexError, ValueError):
        #         print("Invalid choice. Please try again.")

    def end_game(self, payout: float):
        self.game_active = False
        # Only update the player's balance if they won or lost money. If payout is <= 0, it means the player tied or lost.
        # Not withdrawing from the player balance in case of lost since the payout removes the bet amount from the balance,
        # and we don't want to double charge the player.
        if payout > 0:
            self.player.deposit(payout)
        
        self.active_game_manager = None
        self.active_page.build_ui()  # Reset to the main menu after the game ends
