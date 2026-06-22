from casino.casino import Casino
# from casino.player import PlayerController
import os

from nicegui import ui as gui
import ui.routes
from asyncio import run

# from utils.cards import Card, CardView, Rank, Suit
# from casino.games.blackjack.renderer import BlackjackRenderer
# from casino.renderer import CasinoRenderer


# def main():
#     casino = Casino("Python Casino")
#     casino.menu()

async def main_ui():
    casino = Casino("Python Casino")
    await casino.menu()

@gui.page("/")
async def main():
    await main_ui()

if __name__ in {"__main__", "__mp_main__"}:
    if os.getenv("UI"):
        gui.run()
    # else:
    #     main()
