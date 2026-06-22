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
    "chips": "absolute left-9/10 bottom-1/10",
    "pot": "absolute bottom-1/2 left-1/4",
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
        self.active_bets: dict[int, int] = {} # Maps chip value to quantity of that chip currently bet

    @property
    def total_bet(self) -> str:
        total = sum(value * key for key, value in self.active_bets.items())
        return f"Current bet: ${total}" if total > 0 else ""

    def build_ui(self):
        self.container = ui.element('div').classes('relative size-full flex items-stretch justify-between game-container')

        with self.container:
            self.game_area = ui.element('div').classes('relative grow bg-green-700 rounded-lg shadow-lg')
            with self.game_area:
                with ui.element("div").classes(f"{blackjack_table_positions["deck"]} pointer-events-none w-fit"):
                    CardUI(CardView(is_face_up=False))


                self.player_hand = ui.row().classes(blackjack_table_positions["player_cards"])
                self.dealer_hand = ui.row().classes(blackjack_table_positions["dealer_cards"])

                self.pot = ui.label(f"").classes(f"{blackjack_table_positions['pot']} translate-y-10 left-1/2! -translate-x-1/2 text-sm text-white mt-2")
                self.pot.bind_text_from(self, 'total_bet')
                # Chips
                for i, chip in enumerate(self.chips):
                    btn_class = f"{blackjack_table_positions['chips']} -translate-y-[{i*110}%] cursor-pointer disabled:cursor-not-allowed"
                    btn = ui.element("button").classes(btn_class)

                    async def place_bet_closure(v, idx=i):
                        if not self.place_bet_cmd:
                            return
                        
                        cmd = self.place_bet_cmd
                        cmd.parameters[0].value = v
                        self.event_bus.notify(BlackJackCommandRequest.PLACE_BET, cmd)

                        bet_exists = self.active_bets.get(v)

                        if bet_exists and bet_exists > 0:
                            self.active_bets[v] += 1
                        else:
                            self.active_bets[v] = 1

                            # Keep Tailwind for everything except the dynamic math
                            shared_base = "absolute transition-all duration-300 ease-in-out"

                            btn_remove = ui.element("button").classes(f"{shared_base} {blackjack_table_positions['chips']}")
                            # Apply the dynamic Y transform via inline styles
                            btn_remove.style(f"transform: translateY(-{idx*110}%);")

                            with btn_remove:
                                ChipUI(ChipValue(v))

                            await asyncio.sleep(0.01)

                            # Move to pot: update tailwind positions AND clear/override the inline style
                            btn_remove.classes(
                                add=blackjack_table_positions['pot'], 
                                remove=blackjack_table_positions['chips']
                            )
                            # Switch the transform direction via inline style
                            btn_remove.style(f"transform: translateX({idx*110}%);")

                            await asyncio.sleep(0.3)

                            btn_remove.classes("cursor-pointer")

                            with btn_remove:
                                count = ui.label(f"x{self.active_bets.get(v, 0)}").classes("absolute -top-2 -right-2 text-xs font-bold text-white bg-black rounded-full w-5 h-5 flex items-center justify-center")
                                count.bind_text_from(self.active_bets,v, backward=lambda x: f"x{x}")

                            
                            def remove_bet_closure(v, btn: ui.element):
                                if not self.remove_bet_cmd:
                                    return
                                
                                bet_exists = self.active_bets.get(v)

                                if bet_exists and bet_exists > 0:
                                    self.active_bets[v] -= 1

                                    cmd = self.remove_bet_cmd
                                    cmd.parameters[0].value = v
                                    self.event_bus.notify(BlackJackCommandRequest.REMOVE_BET, cmd)

                                    if self.active_bets[v] <= 0:
                                        btn.delete()

                            btn_remove.on("click", lambda _, v=v, btn=btn_remove: remove_bet_closure(v, btn))

                    btn.on("click", lambda _, v=chip.chip_value, idx=i: place_bet_closure(v, idx))
                    
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

    def change_bet(self, _snapshot: BlackjackSnapshot): 
        pass       
        # self.pot.set_text(f"Current Bet: ${sum(value * key for key, value in self.active_bets.items())}")

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
