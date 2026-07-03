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
    
        print(f"Player Funds: ${snapshot.active_player.funds:.2f}")

    def available_commands(self, snapshot: SlotMachineSnapshot) -> list[str]:
        for i, command in enumerate(snapshot.available_commands, start=1):
            print(f"{i}. {command.display_name}")


@dataclass
class BetButton:
    bet_amount: int
    button: ui.button
    enabled: bool

class SlotMachineRenderer(Renderer):
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
        self.container = ui.element('div').classes('prelative size-full flex flex-col items-center justify-end game-container bg-emerald-700')

        # We will store the INNER strips here to animate them later
        self.reels = [] 

        with self.container:
            with ui.element("div").classes("flex flex-col items-center gap-2 h-4/5 bg-gray-900 p-4 rounded-md"):
                self.results_display = ui.label("Welcome to the Slot Machine!").classes('w-2/5 text-center text-lg font-bold mb-4 border-2 border-gray-300 p-2 rounded-md bg-white shadow-2xl shadow-cyan-500/50 ring-4 ring-indigo-500')
                self.reels_container = ui.row().classes('flex items-center justify-center gap-4')

                with self.reels_container:
                    for _ in range(3):
                        # 1. VIEWPORT: Fixed 120px height. Red lines explicitly at 30px.
                        reel_viewport = ui.column().classes(
                            'flex flex-col no-wrap items-center justify-start overflow-hidden relative w-20 bg-white ring-4 ring-red-600 shadow-2xl shadow-red-500/50 '
                            'h-[120px] border-red-500 border-2 '
                            'after:content-[""] after:w-4/5 after:h-1 after:absolute after:bg-red-500 after:top-[30px] '
                            'before:content-[""] before:w-4/5 before:h-1 before:absolute before:bg-red-500 before:bottom-[30px]'
                        )
                        
                        with reel_viewport:
                            # 2. STRIP: gap-0 is critical! pt-[30px] aligns the center slot.
                            strip = ui.column().classes('flex flex-col items-center gap-0 pt-[30px]')
                            
                            with strip:
                                for _ in range(100):
                                    for icon in Reels:
                                        # 3. SYMBOLS: Locked to 60px height.
                                        ui.label(icon.value).classes(
                                            "h-[60px] w-full flex items-center justify-center text-4xl m-0 p-0 leading-none select-none"
                                        )

                        # Initialize the strip one sequence deep so the top "peek" slot isn't empty on load!
                        initial_offset = len(Reels) * 60
                        strip.style(f'transform: translateY(-{initial_offset}px)')
                        self.reels.append(strip)

                self.bet_display = ui.label("Current Bet: $0.00").classes('text-4xl text-white font-bold')
                self.bet_display.bind_text_from(self, "bet", backward=lambda f: f"Current Bet: ${f}")


                with ui.element("div").classes("flex flex-col justify-center items-center gap-4 grow p-10"):
                    self.funds_display = ui.label("Player Funds: $0.00").classes('text-lg text-white font-bold')
                    
                    self.commands_container = ui.element('div').classes('flex flex-col items-center justify-center gap-2')

                    with ui.row().classes('gap-2'):    
                        for bet_amount in [1, 5, 10, 25, 50, 100, 500, 1000]:
                            with ui.column():
                                button_classes = 'disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out'
                                button_add = ui.button(f"+{bet_amount}$", on_click=lambda bet=bet_amount: self.place_bet(bet)).classes(f"{button_classes} bg-green-5 hover:bg-green-6")
                                button_remove = ui.button(f"-{bet_amount}$", on_click=lambda bet=bet_amount: self.place_bet(-bet)).classes(f"{button_classes} bg-red-5 hover:bg-red-6")
                                self.bet_buttons[bet_amount] = BetButton(bet_amount=bet_amount, button=button_add, enabled=True)
                                self.bet_buttons[-bet_amount] = BetButton(bet_amount=-bet_amount, button=button_remove, enabled=True)

                    with ui.column().classes('gap-10 items-center mt-10'):
                        self.spin_button = ui.button("Spin", on_click=lambda: self.event_bus.notify(SlotMachineCommandRequest.SPIN, self.spin_cmd)).classes('bg-red-600! hover:bg-red-700! ring-6 ring-red-800 size-25 rounded-full disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out')
                        self.spin_button.disable()  # Initially disable the spin button
                        self.spin_button.bind_enabled_from(self, "spin_cmd")

                        self.end_button = ui.button("End Game", on_click=lambda: self.event_bus.notify(SlotMachineCommandRequest.END_GAME, self.end_cmd)).classes('bg-red-600! hover:bg-red-700! disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out')
                        self.end_button.bind_enabled_from(self, "end_cmd")

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
        self.funds_display.set_text(f"Player Funds: ${snapshot.active_player.funds:.2f}")
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

        self.results_display.set_text("Spinning!!!")

        # 1. Get the ordered list of all possible Enum members
        all_symbols = list(Reels) 
        
        # 2. Find the integer index for each symbol in the result tuple
        # For the example above, this will generate something like [0, 2, 3]
        winning_indices = [all_symbols.index(symbol) for symbol in snapshot.reels]

        items_per_reel = len(Reels)
        safe_start_offset = items_per_reel * 2
        
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

        # 2. Hardcoded height perfectly matches our CSS
        item_height = 60 
        ms_per_repetition = 150 
        
        current_spins = random.randint(10, 15)

        reel_tasks = []
        total_duration = 0

        for i, strip in enumerate(self.reels):
            if i > 0:
                current_spins += random.randint(4, 8)

            # We add the safe_start offset to ensure we spin past the initial state
            target_item = (current_spins * items_per_reel) + winning_indices[i] + items_per_reel
            
            # The math is now flawlessly exact: index * 60px
            y_offset = target_item * item_height
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
                            // Optional: Reset volume if you plan to play it again later
                            // audio.volume = 1; 
                        }}
                    }}, stepTime);
        ''')
        await asyncio.gather(*reel_tasks)

        spin_audio.delete()

        payout = snapshot.multiplier * snapshot.bet

        if payout > 0:
            self.results_display.set_text(f"You won ${payout}!")
        else:
            self.results_display.set_text("Better luck next time!")

        self.animation_cleared.set()  # Allow player_choice to be called again

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
