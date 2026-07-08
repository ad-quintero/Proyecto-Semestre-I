from nicegui import ui

from utils.cards import CardView, Suit, Rank
from asyncio import sleep

class CardUI:
    def __init__(self, card: CardView):
        self.card = card

        self.suit_colors = {
            Suit.HEARTS: 'text-red-600',
            Suit.DIAMONDS: 'text-red-600',
            Suit.CLUBS: 'text-slate-800',
            Suit.SPADES: 'text-slate-800'
        }

        self.card_container = ui.card().classes('aspect-5/7 h-35 flex items-center justify-center rounded-lg border hover:scale-115 transition-transform duration-200 select-none')
        self.flipping = False

        self.refresh()

    def refresh(self):
        self.card_container.clear()
        with self.card_container:
            if self.card.is_face_up:
                # Top-Left Value & Suit
                with ui.column().classes('absolute top-2 left-2 items-center gap-0 leading-none flex'):
                    ui.label(self.card.rank.value).classes(f'text-lg font-bold {self.suit_colors[self.card.suit]}')

                # Center Large Suit Icon
                ui.label(self.card.suit.value).classes(f'text-xl absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 {self.suit_colors[self.card.suit]}')

                # Bottom-Right Value & Suit (Inverted)
                with ui.column().classes('absolute bottom-2 right-2 items-center gap-0 leading-none rotate-180'):
                    ui.label(self.card.rank.value).classes(f'text-lg font-bold {self.suit_colors[self.card.suit]}')

                # Reset background to white for face-up
                self.card_container.classes(remove='bg-red-800 border-white', add='bg-white')
            else:
                # Face Down - Classic Red Casino Pattern
                ui.label('♠♥\n♦♣').classes('text-white text-xl text-center opacity-30 font-serif whitespace-pre absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2')
                self.card_container.classes(remove='bg-white', add='bg-red-800 border-4 border-white outline outline-1 outline-red-800')

    async def flip(self):
        if self.flipping:
            return  # Prevent multiple flips at the same time
        self.flipping = True

        self.card_container.classes('scale-x-0!')
        await sleep(0.2)

        self.card.is_face_up = not self.card.is_face_up
        self.refresh()

        self.card_container.classes(remove='scale-x-0!')

        self.flipping = False
