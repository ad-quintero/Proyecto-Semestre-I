from utils.renderer import Renderer
from utils.commands.command import CommandSchema
from casino.games.slot_machine.events import SlotMachineCommandRequest, SlotMachineEvents
from casino.games.slot_machine.slot_machine import SlotMachineSnapshot, Reels
from nicegui import ui

from dataclasses import dataclass
import asyncio
import random
from utils import audio

class SlotMachineTerminalRenderer(Renderer):
    def __init__(self, event_bus):
        super().__init__(event_bus)

        self.event_bus.subscribe(SlotMachineEvents.SPIN_RESULT, self.render)
        self.event_bus.subscribe(SlotMachineEvents.PLAYER_CHOICE, self.available_commands)

    def render(self, snapshot: SlotMachineSnapshot):
        print(f"{snapshot.reels[0].value} {snapshot.reels[1].value} {snapshot.reels[2].value}")
        if multiplier := snapshot.multiplier > 1:
            print(f"Congratulations! You won with a multiplier of {snapshot.multiplier}x!")
    
        print(f"Fondos del jugador: ${snapshot.active_player.funds:.2f}")

    def available_commands(self, snapshot: SlotMachineSnapshot) -> list[str]:
        for i, command in enumerate(snapshot.available_commands, start=1):
            print(f"{i}. {command.display_name}")


@dataclass
class BetButton:
    bet_amount: int
    button: ui.button
    enabled: bool

class SlotMachineRenderer(Renderer):
    SYMBOL_HEIGHT = 112
    VIEWPORT_HEIGHT = SYMBOL_HEIGHT * 2
    HALF_SYMBOL = SYMBOL_HEIGHT // 2

    def __init__(self, event_bus):
        super().__init__(event_bus)

        self.event_bus.subscribe(SlotMachineEvents.PLAYER_CHOICE, self.player_choice)
        self.event_bus.subscribe(SlotMachineEvents.SPIN_RESULT, self.spin_results)

        self.bet = 0
        self.container: ui.element = None  # Placeholder for the UI container
        self.results_display: ui.label = None  # Placeholder for the results display

        self.bet_buttons: dict[int, BetButton] = {}
        """Dictionary to hold bet buttons. It's in the format {bet_amount: button_instance}"""
        self.spin_button: ui.button | None = None
        self.end_button: ui.button | None = None

        self.reels: list[ui.element] = []

        self.place_bet_cmd: CommandSchema | None = None
        self.spin_cmd: CommandSchema | None = None
        self.end_cmd: CommandSchema | None = None

        # Async event to signal when the spin animation is complete so player_choice 
        # can be called again. This prevents the player from placing bets or spinning while the animation is still running.
        self.animation_cleared = asyncio.Event()
        self.animation_cleared.set()

    def build_ui(self):
        self.container = ui.element('div').classes('prelative size-full flex flex-col items-center justify-stretch game-container bg-emerald-700')

        # We will store the INNER strips here to animate them later
        self.reels = [] 

        with self.container:
            with ui.element("div").classes("grow w-full flex items-center justify-around p-0").style("background-image: url('assets/images/texture.png'); background-size: cover; background-position: center;"):
                self.results_display = ui.label("Tragamonedas").classes('w-1/4 text-center text-6xl text-white font-bold border-5 border-black p-4 rounded-lg bg-red-800')
                self.reels_container = ui.row().classes('flex items-center justify-center gap-4 bg-[#e0bc62] p-10 rounded-4xl border-10 border-black')

                with self.reels_container:
                    with ui.element("div").classes("flex items-center justify-center gap-10 p-5 border-20 border-red-800 rounded-4xl"):
                        for _ in range(3):
                            # 1. VIEWPORT: Calculated dynamic heights & offsets using inline styles for perfect scaling
                            reel_viewport = ui.column().classes(
                                'flex flex-col no-wrap items-center justify-start overflow-hidden relative w-30 bg-white '
                                'border-black border-5 rounded-lg '
                                'after:content-[""] after:w-4/5 after:h-1 after:absolute after:bg-red-500 '
                                'before:content-[""] before:w-4/5 before:h-1 before:absolute before:bg-red-500'
                            ).style(
                                f'height: {SlotMachineRenderer.VIEWPORT_HEIGHT}px; '
                                f'--after-top: {SlotMachineRenderer.HALF_SYMBOL}px; --before-bottom: {SlotMachineRenderer.HALF_SYMBOL}px;'
                            )
                            # Inject custom CSS properties dynamically to handle the absolute win-lines scaling
                            ui.add_head_html(f'''
                                <style>
                                    [style*="--after-top"]::after {{ top: var(--after-top) !important; }}
                                    [style*="--before-bottom"]::before {{ bottom: var(--before-bottom) !important; }}
                                </style>
                            ''')
                            
                            with reel_viewport:
                                # 2. STRIP: Dynamic padding-top aligns the center slot.
                                strip = ui.column().classes('flex flex-col items-center gap-0').style(f'padding-top: {SlotMachineRenderer.HALF_SYMBOL}px')
                                
                                with strip:
                                    for _ in range(100):
                                        for icon in Reels:
                                            # 3. SYMBOLS: Height set dynamically from SlotMachineRenderer.SYMBOL_HEIGHT variable
                                            ui.label(icon.value).classes(
                                                "w-full flex items-center justify-center text-7xl m-0 p-0 leading-none select-none"
                                            ).style(f'height: {SlotMachineRenderer.SYMBOL_HEIGHT}px')

                            # Initialize the strip one sequence deep so the top "peek" slot isn't empty on load!
                            initial_offset = len(Reels) * SlotMachineRenderer.SYMBOL_HEIGHT
                            strip.style(f'transform: translateY(-{initial_offset}px)')
                            self.reels.append(strip)

                ui.image("assets/images/logo.svg").classes('w-1/5 h-auto self-start mt-10')

            with ui.element("div").classes("grow w-full flex flex-col justify-center items-center gap-10 p-10 bg-[#1b0047]"):
                with ui.element("div").classes("flex gap-4 text-white text-4xl gap-10"):
                    self.bet_display = ui.label("Apuesta: $0.00")
                    self.bet_display.bind_text_from(self, "bet", backward=lambda f: f"Apuesta: ${f}")

                    self.funds_display = ui.label("Fondos del Jugador: $0.00")

                with ui.row().classes('gap-2'):    
                    for bet_amount in [1, 5, 10, 25, 50, 100, 500, 1000]:
                        with ui.column():
                            button_classes = 'disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out text-4xl w-30 rounded-md p-2 min-h-0'
                            button_add = ui.button(f"+{bet_amount}", on_click=lambda bet=bet_amount: self.place_bet(bet)).classes(f"{button_classes} bg-green-8 hover:bg-green-9")
                            button_remove = ui.button(f"-{bet_amount}", on_click=lambda bet=bet_amount: self.place_bet(-bet)).classes(f"{button_classes} bg-[#cf035c]! hover:brightness-115")
                            self.bet_buttons[bet_amount] = BetButton(bet_amount=bet_amount, button=button_add, enabled=True)
                            self.bet_buttons[-bet_amount] = BetButton(bet_amount=-bet_amount, button=button_remove, enabled=True)

                with ui.column().classes('gap-10 items-center mt-10'):
                    self.end_button = ui.button("Finalizar", on_click=lambda: self.event_bus.notify(SlotMachineCommandRequest.END_GAME, self.end_cmd)).classes('bg-yellow-400! hover:bg-yellow-500! text-black font-bold text-2xl rounded-md disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out')
                    self.end_button.bind_enabled_from(self, "end_cmd")

                self.spin_button = ui.button("PRESIONAR", on_click=lambda: self.event_bus.notify(SlotMachineCommandRequest.SPIN, self.spin_cmd)).classes('bg-transparent! size-55 text-xl rounded-full disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out absolute right-40')
                self.spin_button.style("background-image: url('assets/images/button.png') !important; background-size: cover !important; background-position: center !important;")
                self.spin_button.disable()  # Initially disable the spin button
                self.spin_button.bind_enabled_from(self, "spin_cmd")

    def place_bet(self, amount: int):
        if self.place_bet_cmd:
            with self.container:
                audio.play_audio("casino/button.mp3")

            cmd = self.place_bet_cmd
            cmd.parameters[0].value = amount
            self.event_bus.notify(SlotMachineCommandRequest.CHANGE_BET, cmd)

    async def player_choice(self, snapshot: SlotMachineSnapshot):
        await self.animation_cleared.wait()  # Wait for any ongoing animation to finish

        self.bet = snapshot.bet
        self.funds_display.set_text(f"Fondos del jugador: ${snapshot.active_player.funds:.2f}")
        self._setup_commands(snapshot)

    async def spin_results(self, snapshot: SlotMachineSnapshot):
        self.animation_cleared.clear()  # Block player_choice until the animation is done

        # Disable all buttons to show the spin animation
        self.spin_cmd = None
        self.end_cmd = None
        for bet_button in self.bet_buttons.values():
            bet_button.button.disable()

        with self.container:
            spin_audio = audio.play_audio("slot_machine/spin_loop.mp3", True).classes("spin-audio")

        self.results_display.set_text("Girando!!!")

        # 1. Get the ordered list of all possible Enum members
        all_symbols = list(Reels) 
        
        # 2. Find the integer index for each symbol in the result tuple
        winning_indices = [all_symbols.index(symbol) for symbol in snapshot.reels]

        items_per_reel = len(Reels)
        
        # Redefined inside functions locally to ensure scope sync
        safe_start_offset = items_per_reel * 2 * SlotMachineRenderer.SYMBOL_HEIGHT
        
        for strip in self.reels:
            strip.style(f'transition: none; transform: translateY(-{safe_start_offset}px);')
            
        await asyncio.sleep(0.05) 
        
        async def animate_reel(index, strip, duration_ms, target_y):
            strip.style(
                f'transition: transform {duration_ms}ms cubic-bezier(0.15, 0.85, 0.3, 1); '
                f'transform: translateY(-{target_y}px);'
            )
            await asyncio.sleep(duration_ms / 1000.0)
            with self.container:
                # Play the stop sound for THIS reel
                audio.play_audio("slot_machine/spin_end.mp3")

        ms_per_repetition = 150 
        current_spins = random.randint(10, 15)

        reel_tasks = []
        total_duration = 0

        for i, strip in enumerate(self.reels):
            if i > 0:
                current_spins += random.randint(4, 8)

            # We add the safe_start offset to ensure we spin past the initial state
            target_item = (current_spins * items_per_reel) + winning_indices[i] + items_per_reel
            
            # Size Independent Math: total item position multiplied safely by dynamic variable
            y_offset = target_item * SlotMachineRenderer.SYMBOL_HEIGHT
            duration_ms = current_spins * ms_per_repetition
            total_duration += duration_ms
            
            reel_tasks.append(asyncio.create_task(animate_reel(i, strip, duration_ms, y_offset)))

        with self.container:
            ui.run_javascript(f'''
                    const audio = document.getElementsByClassName("spin-audio")[0];
                          
                    const stepTime = 50; // Update every 50ms for smooth transitions
                    const steps = {total_duration} / stepTime;
                    const volumeStep = audio.volume / steps;

                    const fadeInterval = setInterval(() => {{
                        if (audio.volume > volumeStep) {{
                            audio.volume -= volumeStep;
                        }} else {{
                            audio.volume = 0;
                            audio.pause();
                            clearInterval(fadeInterval);
                        }}
                    }}, stepTime);
        ''')
        await asyncio.gather(*reel_tasks)

        spin_audio.delete()

        payout = snapshot.multiplier * snapshot.bet

        if payout > 0:
            self.results_display.set_text(f"Ganaste ${payout}!")
        else:
            self.results_display.set_text("¡Mejor suerte la próxima vez!")

        self.animation_cleared.set()    
        
    def _setup_commands(self, snapshot: SlotMachineSnapshot):
        self.spin_cmd = snapshot.available_commands.get(SlotMachineCommandRequest.SPIN)
        self.end_cmd = snapshot.available_commands.get(SlotMachineCommandRequest.END_GAME)

        # Disable all buttons first
        for bet_button in self.bet_buttons.values():
            bet_button.button.disable()


        # Enable buttons based on available commands
        if SlotMachineCommandRequest.CHANGE_BET in snapshot.available_commands:
            self.place_bet_cmd = snapshot.available_commands[SlotMachineCommandRequest.CHANGE_BET]

            for bet_button in self.bet_buttons.values():
                if bet_button.bet_amount > 0:
                    # Enable "+" buttons if the player's total wallet can cover the increased bet
                    can_afford = (self.bet + bet_button.bet_amount) <= snapshot.active_player.funds
                    bet_button.button.set_enabled(can_afford)
                    
                elif bet_button.bet_amount < 0:
                    # Enable "-" buttons only if lowering the bet doesn't drop the current bet below 0
                    # (Remember: bet_button.bet_amount is negative here, like -10)
                    can_lower = (self.bet + bet_button.bet_amount) >= 0
                    bet_button.button.set_enabled(can_lower)
