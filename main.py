from casino.casino import Casino
from casino.player import PlayerController
import os

import flet as ft
from ui.models.cards import CardControl
from utils.cards import Card, CardView, Rank, Suit
from pathlib import Path



def main():
    casino = Casino("Python Casino")
    casino.menu()

def ui(page: ft.Page):
    card = Card(suit=Suit.SPADES, rank=Rank.ACE)

    page.title = "Digital Casino"
    page.add(CardControl(CardView.from_card(card)))


if __name__ == "__main__":
    if os.getenv("UI"):
        ft.run(ui)
    else:
        main()
