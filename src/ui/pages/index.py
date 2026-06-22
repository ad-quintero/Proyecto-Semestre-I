from nicegui import ui

class IndexPage:
    def __init__(self):
        ui.label("Welcome to the Casino!").classes('text-2xl font-bold mb-4')
        ui.label("Please select a game to play:").classes('text-lg mb-2')

        with ui.column().classes('gap-2'):
            ui.link("Blackjack", "/blackjack").classes('w-full')
            ui.link("Poker (Coming Soon)", "/poker").classes('w-full')
            ui.link("Roulette (Coming Soon)", "/roulette").classes('w-full')
