from nicegui import ui
from .models.card import CardUI
from utils.cards import CardView, Suit, Rank
from .pages import index

from casino.games.blackjack.renderer import BlackjackRenderer

@ui.page("/")
def main():
    index.IndexPage()
