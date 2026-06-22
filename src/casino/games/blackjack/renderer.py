from utils.commands.command import CommandSchema
from utils.event_listener import EventBus
from utils.renderer import Renderer
from . import BlackJackCommandRequest, BlackjackEvent, BlackjackPhase
from .commands import HitCommand, StandCommand
from .blackjack import BlackjackSnapshot
from utils.cards import Card, CardView
from casino.games import GenericEvent
from typing import TypedDict

from ui.models.card import CardUI
from ui.models.chips import ChipUI, ChipValue
from nicegui import ui, binding
import asyncio

from dataclasses import dataclass

class BlackjackTerminalRenderer(Renderer):
    player_hand: list[CardView] = []
    dealer_hand: list[CardView] = []

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.event_bus.subscribe(BlackjackEvent.PLAYER_HIT, self.player_hit)
        self.event_bus.subscribe(BlackjackEvent.DEALER_HIT, self.dealer_hit)
        self.event_bus.subscribe(BlackjackEvent.DEALER_WINS, self.dealer_wins)
        self.event_bus.subscribe(BlackjackEvent.PLAYER_WINS, self.player_wins)
        self.event_bus.subscribe(GenericEvent.PHASE_CHANGE, self.handle_phase_change)

        self.player_cards = []
        self.dealer_cards = []

    def show_available_commands(self, snapshot: BlackjackSnapshot):
        print("Available Commands:")
        for i, cmd in enumerate(snapshot.available_commands):
            print(f"{i+1} {cmd.display_name}.")

    def player_hit(self, snapshot: BlackjackSnapshot):
        self.player_cards = snapshot.player_cards
        if snapshot.active_player:
            self._render_table(f"{snapshot.active_player.name} Hits")

    def dealer_hit(self, snapshot: BlackjackSnapshot):
        self.dealer_cards = snapshot.dealer_cards
        self._render_table("Dealer Hits")

    def handle_phase_change(self, state: tuple[BlackjackPhase, BlackjackSnapshot]):
        new_phase, snapshot = state
        if new_phase == BlackjackPhase.PLAYER_TURN:
            self.show_available_commands(snapshot)

    def dealer_wins(self, snapshot: BlackjackSnapshot):
        self.dealer_cards = snapshot.dealer_cards
        self.player_cards = snapshot.player_cards
        self._render_table(f"Dealer Wins. You lose your bet (${abs(snapshot.payout)}).")

    def player_wins(self, snapshot: BlackjackSnapshot):
        self.dealer_cards = snapshot.dealer_cards
        self.player_cards = snapshot.player_cards
        self._render_table(
            f"Congratulations {snapshot.active_player.name}, you win! You gain ${snapshot.payout}."
        )

    def _render_table(self, msg: str):
        print(f"--- {msg} ---")
        print(f"Player's Hand: {', '.join(str(card) for card in self.player_cards)}")
        print(f"Dealer's Hand: {', '.join(str(card) for card in self.dealer_cards)}")

blackjack_table_positions = {
    "deck": "absolute left-9/10 top-10 rotate-45",
    "chips": "absolute left-9/10 bottom-10",
    "dealer_cards": "absolute top-10 left-1/2 -translate-x-1/2",
    "player_cards": "absolute top-8/10 left-1/2 -translate-x-1/2",
    "buttons": "absolute top-1/2 right-5 -translate-x-1/2",
    "player_data": "absolute top-8/10 left-1/2 -translate-x-1/2",
}

@dataclass
class PlaceBetData:
    chip_value: int
    can_place_bet: bool

class BlackjackRenderer(Renderer):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)

        self.event_bus.subscribe(GenericEvent.PHASE_CHANGE, self.turn_start)
        self.event_bus.subscribe(BlackjackEvent.PLAYER_HIT, self.player_hit)
        self.event_bus.subscribe(BlackjackEvent.DEALER_HIT, self.dealer_hit)
        self.event_bus.subscribe(BlackjackEvent.PLACE_BET, self.change_bet)
        self.event_bus.subscribe(BlackjackEvent.REMOVE_BET, self.change_bet)
        # self.event_bus.subscribe(BlackjackEvent.DEALER_WINS, self.dealer_wins)
        # self.event_bus.subscribe(BlackjackEvent.PLAYER_WINS, self.player_wins)
        # self.event_bus.subscribe(GenericEvent.PHASE_CHANGE, self.handle_phase_change)

        self.container: ui.element = None
        self.game_area: ui.element = None

        self.can_place_bets = False
        self.place_bet_cmd: CommandSchema = None
        self.remove_bet_cmd: CommandSchema = None

        self.chips = [PlaceBetData(chip_value=chip.value, can_place_bet=False) for chip in ChipValue]

    def build_ui(self):
        self.container = ui.element('div').classes('relative size-full flex items-stretch justify-between game-container')

        with self.container:
            self.game_area = ui.element('div').classes('relative grow bg-green-700 rounded-lg shadow-lg')
            with self.game_area:
                with ui.element("div").classes(f"{blackjack_table_positions["deck"]} pointer-events-none w-fit"):
                    CardUI(CardView(is_face_up=False))


                self.player_hand = ui.row().classes(blackjack_table_positions["player_cards"])
                self.dealer_hand = ui.row().classes(blackjack_table_positions["dealer_cards"])
            
                for i, chip in enumerate(self.chips):
                    def place_bet_closure(v):
                        if not self.place_bet_cmd:
                            return

                        cmd = self.place_bet_cmd
                        cmd.parameters[0].value = v
                        self.event_bus.notify(BlackJackCommandRequest.PLACE_BET, cmd)

                    btn = ui.element("button").classes(f"{blackjack_table_positions['chips']} chips -translate-y-[{i*110}%] cursor-pointer disabled:cursor-not-allowed").on("click", lambda _, v=chip.chip_value: place_bet_closure(v))
                    
                    binding.bind_to(
                        self.chips[i], 'can_place_bet', 
                        btn.props, 'disabled', 
                        forward=lambda can_place: not can_place
                    )

                    with btn:
                        ChipUI(ChipValue(chip.chip_value))
            
            self.command_area = ui.column(align_items="center").classes("basis-1/4 flex flex-col items-center justify-center bg-red-300")
    
    def turn_start(self, data: tuple[BlackjackPhase, BlackjackSnapshot]):
        new_phase, snapshot = data
        if new_phase == BlackjackPhase.PLAYER_TURN:
            with self.command_area:
                    self.command_area.clear()

                    with ui.column().classes('w-full flex flex-col items-center gap-4 mt-4'):
                        ui.label(f"{snapshot.active_player.name}").classes('text-xl font-bold mb-4')
                        ui.label(f"Balance: ${snapshot.active_player.balance}").classes('text-lg mb-4')

                    ui.label("Available Commands").classes('text-lg font-bold mb-2')

                    enums = snapshot.available_commands.keys()
                    self.can_place_bets = BlackJackCommandRequest.PLACE_BET in enums or BlackJackCommandRequest.REMOVE_BET in enums

                    for enum, cmd in snapshot.available_commands.items():
                        if enum not in (BlackJackCommandRequest.PLACE_BET, BlackJackCommandRequest.REMOVE_BET):
                            ui.button(cmd.display_name, on_click=lambda _, cmd=cmd: self.event_bus.notify(enum, cmd))
                        else:
                            self.place_bet_cmd = cmd if enum == BlackJackCommandRequest.PLACE_BET else self.place_bet_cmd
                            self.remove_bet_cmd = cmd if enum == BlackJackCommandRequest.REMOVE_BET else self.remove_bet_cmd

                            for chip in self.chips:
                                chip.can_place_bet = snapshot.active_player.balance >= chip.chip_value and self.can_place_bets

    def change_bet(self, snapshot: BlackjackSnapshot):
        # This is a placeholder for handling bet changes in the UI. You can implement a bet slider or input field here.
        pass

    async def player_hit(self, snapshot: BlackjackSnapshot):
        # Keep the master container open so NiceGUI knows where to position these root containers
        card = snapshot.player_cards[-1]
        idx = len(snapshot.player_cards) - 1
        card_pos = f"{blackjack_table_positions['player_cards']} translate-x-{idx}/1"

        flying_card = None
    
        with self.game_area:
            # Create the flying card container at the deck position
            flying_card = ui.element("span").classes(f"{blackjack_table_positions['deck']} pointer-events-none transition-all duration-500")

            # 3. Use the 'with' block ONLY to build the inner card structure
            with flying_card:
                card.is_face_up = False  # Start face down for the animation
                dealt_card = CardUI(card)
            
        await asyncio.sleep(0.05)
            
        flying_card.classes(
            add=card_pos, 
            remove=blackjack_table_positions['deck']
        )

        # 5. NOW it is safe to sleep! The slot stack is perfectly clean.
        await asyncio.sleep(0.5)
        
        await dealt_card.flip()
        flying_card.classes.remove('pointer-events-none')

    async def dealer_hit(self, snapshot: BlackjackSnapshot):
        card = snapshot.dealer_cards[-1]
        idx = len(snapshot.dealer_cards) - 1
        card_pos = f"{blackjack_table_positions['dealer_cards']} translate-x-{idx}/1"

        is_face_up = card.is_face_up

        flying_card = None
    
        with self.game_area:
            # Create the flying card container at the deck position
            flying_card = ui.element("span").classes(f"{blackjack_table_positions['deck']} pointer-events-none transition-all duration-500")

            # 3. Use the 'with' block ONLY to build the inner card structure
            with flying_card:
                card.is_face_up = False  # Start face down for the animation
                dealt_card = CardUI(card)
            
        await asyncio.sleep(0.05)
            
        flying_card.classes(
            add=card_pos, 
            remove=blackjack_table_positions['deck']
        )

        # 5. NOW it is safe to sleep! The slot stack is perfectly clean.
        await asyncio.sleep(0.5)
        
        if is_face_up:
            await dealt_card.flip()

# TODO Animation to draw chips to the table when placing bets, and remove them when removing bets. This will likely involve creating temporary flying chip elements similar to the flying cards in the hit animations, and animating them from the chip area to the player's betting area (and vice versa).
