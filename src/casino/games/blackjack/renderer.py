from utils.commands.command import CommandSchema
from utils.event_listener import EventBus
from utils.renderer import Renderer
from . import BlackJackCommandRequest, BlackjackEvent, BlackjackPhase
from .blackjack import BlackjackSnapshot
from utils.cards import Card, CardView
from casino.games import GenericEvent

from ui.models.card import CardUI
from ui.models.chips import ChipUI, ChipValue
from nicegui import ui, binding
import asyncio
from utils.audio import play_random_sound_from_directory, play_audio

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
    "deck": "absolute left-4/5 top-15 rotate-45",
    "chips": "absolute left-9/10 bottom-1/10",
    "pot": "absolute bottom-1/2 left-1/4",
    "dealer_cards": "absolute top-10 left-2/5 -translate-x-1/2",
    "player_cards": "absolute top-8/10 left-2/5 -translate-x-1/2",
    "buttons": "absolute top-1/2 right-5 -translate-x-1/2",
    "player_data": "absolute top-8/10 left-1/2 -translate-x-1/2",
}

@dataclass
class PlaceBetData:
    chip_value: int
    can_place_bet: bool

class BlackjackRenderer(Renderer):
    cards: list[tuple[ui.element, CardUI]]
    placed_chips: list[ui.element]

    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)

        self.event_bus.subscribe(GenericEvent.PHASE_CHANGE, self.turn_start)
        self.event_bus.subscribe(BlackjackEvent.PLAYER_HIT, self.player_hit)
        self.event_bus.subscribe(BlackjackEvent.DEALER_HIT, self.dealer_hit)
        self.event_bus.subscribe(BlackjackEvent.DEALER_WINS, self.dealer_wins)
        self.event_bus.subscribe(BlackjackEvent.PLAYER_WINS, self.player_wins)
        self.event_bus.subscribe(BlackjackEvent.TIE, self.tie)
        self.event_bus.subscribe(BlackjackEvent.NEW_ROUND, self.reset_ui)

        self.container: ui.element = None
        self.game_area: ui.element = None
        self.command_area: ui.element = None

        self.can_place_bets = False
        self.place_bet_cmd: CommandSchema = None
        self.remove_bet_cmd: CommandSchema = None
        self.restart_round_cmd: CommandSchema = None
        self.end_game_cmd: CommandSchema = None

        self.cards = []
        self.placed_chips = []
        self.command_buttons: list[ui.element] = []

        self.chips = [PlaceBetData(chip_value=chip.value, can_place_bet=False) for chip in ChipValue]
        self.active_bets: dict[int, int] = {} # Maps chip value to quantity of that chip currently bet

    @property
    def total_bet(self) -> str:
        total = sum(value * key for key, value in self.active_bets.items())
        return f"Apuesta Total: ${total}" if total > 0 else ""

    def build_ui(self):
        if self.container is None:
            self.container = ui.element('div').classes('relative size-full flex items-stretch justify-between game-container')

        with self.container:
            if not self.game_area:
                self.game_area = ui.element('div').classes('relative grow').style("background-image: url('assets/images/texture.png'); background-size: cover; background-position: center;")
            with self.game_area:
                ui.image("assets/images/logo.svg").classes("absolute top-10 left-10 w-90 h-auto user-select-none pointer-events-none")

                blackjack_text = '''
                    <svg viewBox="0 0 500 200" width="100%" height="auto">
                    <path id="curve" d="M 50,150 Q 250,50 450,150" fill="transparent" />
                    
                    <text font-family="Times New Roman, serif" font-size="90" fill="white">
                        <textPath href="#curve" startOffset="50%" text-anchor="middle">
                        Blackjack
                        </textPath>
                    </text>
                    </svg>
                '''

                with ui.element("div").classes("absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center"):
                    ui.html(blackjack_text)

                with ui.element("div").classes(f"{blackjack_table_positions["deck"]} pointer-events-none w-fit"):
                    CardUI(CardView(is_face_up=False))


                self.player_hand = ui.row().classes(blackjack_table_positions["player_cards"])
                self.dealer_hand = ui.row().classes(blackjack_table_positions["dealer_cards"])

                self.pot = ui.label(f"").classes(f"{blackjack_table_positions['pot']} translate-y-50 left-1/2! -translate-x-1/2 text-4xl text-white bg-pink-600 rounded-lg p-2 font-bold empty:p-0")
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
                            self.placed_chips.append(btn_remove)

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

                            with self.container:
                                play_random_sound_from_directory("assets/sfx/blackjack/chip")  # Play a random chip sound
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
            
                       
                end_game_btn = ui.button("Finalizar", on_click=lambda _: self.event_bus.notify(BlackJackCommandRequest.END, self.end_game_cmd)).classes("absolute bottom-10 left-10 bg-yellow-500! hover:bg-yellow-600! text-black text-4xl font-bold py-2 px-4 rounded disabled:opacity-50 disabled:cursor-not-allowed")
                end_game_btn.bind_enabled_from(self, 'cards', backward=lambda cards: len(cards) == 0)


            if not self.command_area:
                with ui.column().classes("basis-1/4 flex flex-col items-center justify-around bg-[#1b0047] text-white"):
                    ui.image("assets/images/logo_blackjack.png").classes("w-full h-auto")
                    self.command_area = ui.column(align_items="center").classes("relative flex flex-col items-center justify-around text-white w-full")

    def reset_ui(self, _):
        self.active_bets.clear()
        
        for element, _ in self.cards:
            element.delete()
        self.cards.clear()

        for chip in self.placed_chips:
            chip.delete()
        self.placed_chips.clear()
        
        self.place_bet_cmd = None
        self.remove_bet_cmd = None
        self.can_place_bets = True
        
        # Clear the internal elements cleanly without deleting the structural layout containers
        if self.game_area:
            self.game_area.clear()
        if self.command_area:
            self.command_area.clear()
            
        # Rebuild the table structural children
        self.build_ui()

    def turn_start(self, data: tuple[BlackjackPhase, BlackjackSnapshot]):
        new_phase, snapshot = data

        self.can_place_bets = not snapshot.player_cards and not snapshot.dealer_cards
        self.end_game_cmd = snapshot.available_commands.get(BlackJackCommandRequest.END)

        if new_phase == BlackjackPhase.PLAYER_TURN:
            with self.command_area:
                    self.command_area.clear()
                    with ui.column().classes('w-full flex flex-col items-center gap-4 mt-4'):
                        ui.label(f"{snapshot.active_player.name}").classes('text-4xl font-bold mb-4 font-bold')
                        ui.label(f"Balance de jugador: ${snapshot.active_player.balance}").classes('text-xl mb-4')

                    ui.label("Comandos disponibles").classes('text-4xl font-bold mb-10')

                    enums = snapshot.available_commands.keys()
                    self.can_place_bets = BlackJackCommandRequest.PLACE_BET in enums or BlackJackCommandRequest.REMOVE_BET in enums

                    self.command_buttons.clear()
                    for enum, cmd in snapshot.available_commands.items():
                        if enum not in (BlackJackCommandRequest.PLACE_BET, BlackJackCommandRequest.REMOVE_BET, BlackJackCommandRequest.RESET, BlackJackCommandRequest.END):
                            btn = ui.button(cmd.display_name, on_click=lambda _, cmd=cmd: self.event_bus.notify(enum, cmd)).classes("w-1/2 text-4xl mb-10")
                            self.command_buttons.append(btn)
                        else:
                            self.place_bet_cmd = cmd if enum == BlackJackCommandRequest.PLACE_BET else self.place_bet_cmd
                            self.remove_bet_cmd = cmd if enum == BlackJackCommandRequest.REMOVE_BET else self.remove_bet_cmd

                            for chip in self.chips:
                                chip.can_place_bet = snapshot.active_player.balance >= chip.chip_value and self.can_place_bets

        elif new_phase == BlackjackPhase.ROUND_END:
            for btn in self.command_buttons:
                btn.delete()
            self.restart_round_cmd = snapshot.available_commands.get(BlackJackCommandRequest.RESET)

    async def player_hit(self, snapshot: BlackjackSnapshot):
        # Keep the master container open so NiceGUI knows where to position these root containers
        card = snapshot.player_cards[-1]
        idx = len(snapshot.player_cards) - 1
        card_pos = f"{blackjack_table_positions['player_cards']} translate-x-[{idx * 110}%]"

        flying_card = None
    
        with self.game_area:
            # Create the flying card container at the deck position
            flying_card = ui.element("span").classes(f"{blackjack_table_positions['deck']} pointer-events-none transition-all duration-500")

            # 3. Use the 'with' block ONLY to build the inner card structure
            with flying_card:
                card.is_face_up = False  # Start face down for the animation
                dealt_card = CardUI(card)
            
                self.cards.append((flying_card, dealt_card))
            
        await asyncio.sleep(0.05)
            
        flying_card.classes(
            add=card_pos, 
            remove=blackjack_table_positions['deck']
        )

        with self.container:
            play_random_sound_from_directory("assets/sfx/card")  # Play a random card sound

        # 5. NOW it is safe to sleep! The slot stack is perfectly clean.
        await asyncio.sleep(0.5)
        
        await dealt_card.flip()
        flying_card.classes.remove('pointer-events-none')

    async def dealer_hit(self, snapshot: BlackjackSnapshot):
        card = snapshot.dealer_cards[-1]
        idx = len(snapshot.dealer_cards) - 1
        card_pos = f"{blackjack_table_positions['dealer_cards']} translate-x-[{idx * 110}%]"

        is_face_up = card.is_face_up

        flying_card = None
    
        with self.game_area:
            # Create the flying card container at the deck position
            flying_card = ui.element("span").classes(f"{blackjack_table_positions['deck']} pointer-events-none transition-all duration-500")

            # 3. Use the 'with' block ONLY to build the inner card structure
            with flying_card:
                card.is_face_up = False  # Start face down for the animation
                dealt_card = CardUI(card)
                self.cards.append((flying_card, dealt_card))
            
        await asyncio.sleep(0.05)
            
        flying_card.classes(
            add=card_pos, 
            remove=blackjack_table_positions['deck']
        )

        with self.container:
            play_random_sound_from_directory("assets/sfx/card")  # Play a random card sound


        # 5. NOW it is safe to sleep! The slot stack is perfectly clean.
        await asyncio.sleep(0.5)
        
        if is_face_up:
            await dealt_card.flip()

    async def player_wins(self, snapshot: BlackjackSnapshot):
        await asyncio.sleep(1)  # Wait for any ongoing animations to finish
        await self._reveal_all_cards()
        await asyncio.sleep(2)

        with self.container:
            play_audio("casino/win.mp3")

        self._show_end_modal(f"¡Ganaste! Pago: ${abs(snapshot.payout)}")

    async def dealer_wins(self, snapshot: BlackjackSnapshot):
        await asyncio.sleep(1)  # Wait for any ongoing animations to finish
        await self._reveal_all_cards()
        await asyncio.sleep(2)

        with self.container:
            play_audio("casino/lose.mp3")

        self._show_end_modal(f"¡El dealer gana! Pierdes tu apuesta (${abs(snapshot.payout)}).")

    async def tie(self, snapshot: BlackjackSnapshot):
        await asyncio.sleep(1)  # Wait for any ongoing animations to finish
        await self._reveal_all_cards()
        await asyncio.sleep(2)

        with self.container:
            play_audio("casino/lose.mp3")

        self._show_end_modal(f"¡Empate! Tu apuesta (${abs(snapshot.payout)}) es devuelta.")

    async def _reveal_all_cards(self):
        for _, card in self.cards:
            if not card.card.is_face_up:
                await card.flip()

    def _show_end_modal(self, msg: str):
        with self.container:
            dialog = ui.dialog(value=True).classes("w-1/3 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2")

        async def reset_game():
            if self.restart_round_cmd:
                dialog.close()
                await asyncio.sleep(0.1)  # Ensure the dialog is closed before resetting the UI

                self.event_bus.notify(BlackJackCommandRequest.RESET, self.restart_round_cmd)

        def end_game():
            if self.end_game_cmd:
                self.event_bus.notify(BlackJackCommandRequest.END, self.end_game_cmd)
            dialog.close()

        with dialog:
            with ui.element("div").classes("flex flex-col"):
                ui.label(msg).classes("text-3xl text-white font-bold mb-4")

                with ui.row().classes("justify-center gap-4"):
                    ui.button("Cerrar", on_click=end_game)
                    ui.button("Nueva Partida", on_click=reset_game)


