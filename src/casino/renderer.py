from typing import Callable, Literal
from nicegui import ui
from utils.renderer import Renderer

class CasinoRenderer:
    """The main renderer for the casino, responsible for rendering the main menu and handling game selection."""
    
    def __init__(self, on_game_selected: Callable[[Literal["Blackjack", "Poker", "Slot Machine", "Roulette"]], None]):
        self.on_game_selected = on_game_selected

        self.container = ui.element('div').classes('fixed top-0 left-0 right-0 bottom-0')

    def build_ui(self, game_to_render: Renderer = None):
        self.container.clear()
        with self.container:
            if game_to_render is not None:
                game_to_render.build_ui()
            else:
                ui.label("Welcome to the Casino! Please select a game:")
                with ui.element('div').classes('w-full flex flex-col items-center gap-4 mt-4'):
                    ui.button("Blackjack", on_click=lambda: self.on_game_selected("Blackjack"))
                    ui.button("Poker", on_click=lambda: self.on_game_selected("Poker"))
                    ui.button("Slot Machine", on_click=lambda: self.on_game_selected("Slot Machine"))
                    ui.button("Roulette", on_click=lambda: self.on_game_selected("Roulette"))

