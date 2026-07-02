from utils.commands.command import CommandSchema
from utils.renderer import Renderer
from utils.event_listener import EventBus
from casino.games.roulette.roulette import RouletteSnapshot, RouletteCell, Color
from casino.games.roulette import bets
from casino.games.roulette.events import RouletteCommandRequest, RouletteEvents
from casino.games.generic_events import GenericEvent

from nicegui import ui
from nicegui.events import ClickEventArguments

import random
import asyncio

class RouletteRenderer(Renderer):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.event_bus.subscribe(RouletteEvents.BET_PLACED, self.on_bet) 
        self.event_bus.subscribe(RouletteEvents.BET_REMOVED, self.on_bet)
        self.event_bus.subscribe(RouletteEvents.SPIN_RESULT, self.on_spin_result)
        self.event_bus.subscribe(RouletteEvents.PLAYER_TURN_START, self.show_commands)

    def on_bet(self, snapshot: RouletteSnapshot):
        print(f"Bets: {list(snapshot.bets.values())}")

    def on_spin_result(self, snapshot: RouletteSnapshot):
        print(f"Spin result: {snapshot.landing_cell}")
        if snapshot.payouts:
            print("Winning bets:")
            for bet in snapshot.payouts:
                print(f" Winning: - {bet}")

            total_earnings = sum(bet.earnings() for bet in snapshot.payouts)
            print(f"Total earnings: ${total_earnings}")
        else:
            print("No winning bets this round.")

    def show_commands(self, snapshot: RouletteSnapshot):
        print("Available commands:")
        for i, command in enumerate(snapshot.available_commands):
            print(f" - {i + 1}. {command.display_name}")


ROULETTE_ORDER = [0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26]

class RouletteRenderer(Renderer):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self.event_bus.subscribe(RouletteEvents.BET_PLACED, self.on_bet) 
        self.event_bus.subscribe(RouletteEvents.BET_REMOVED, self.on_bet)
        self.event_bus.subscribe(RouletteEvents.SPIN_RESULT, self.on_spin_result)
        self.event_bus.subscribe(RouletteEvents.PLAYER_TURN_START, self.setup_commands)
        self.event_bus.subscribe(RouletteEvents.BETS_CLEARED, self.clear_bets)

        self.container: ui.element = None
        self.wheel: ui.element = None
        self.bets_table: ui.element = None
        self.bets_buttons: ui.element = None

        self.place_bet_cmd: CommandSchema | None = None
        self.remove_bet_cmd: CommandSchema | None = None
        self.clear_bets_cmd: CommandSchema | None = None
        self.spin_wheel_cmd: CommandSchema | None = None
        self.end_game_cmd: CommandSchema | None = None

        self.bet_slider: ui.slider = None
        self.bet_number: ui.number = None
        self.total_bet_display: ui.label = None
        self.winning_bets_display: ui.label = None

        self.chips: dict[str, ui.button] = {}

        self.can_place_bet = True

        # The current rotation of the wheel in degrees. This is used to animate the wheel spinning.
        self.current_rotation = 0
        self.spin_signal = asyncio.Event()
        self.spin_signal.set()

    def build_ui(self):
        if not self.container:
            self.container = ui.element("div").classes("size-full flex justify-center items-center gap-10 bg-emerald-700")

            with self.container:
                with ui.element("div").classes("relative rounded-full"):
                    ui.element("div").classes("absolute [clip-path:polygon(0_0,100%_0,50%_100%)] h-5 w-10 bg-fuchsia-500 left-1/2 -translate-x-1/2 -top-7")

                    with ui.element("div").classes("flex flex-col items-center justify-center gap-5"):
                        if not self.wheel:
                            self.wheel = ui.element("div").classes("relative size-90 rounded-full transition-transform duration-1000 ease-in-out")

                        cell_size = 360 / len(ROULETTE_ORDER)
                        self.wheel.style(f"transform: rotate({self.current_rotation}deg);")
                        with self.wheel:
                            ui.element("div").classes("absolute size-full rounded-full bg-transparent inset-ring-10 inset-ring-orange-800 z-10 after:content-[''] after:absolute after:top-1/2 after:left-1/2 after:-translate-x-1/2 after:-translate-y-1/2 after:size-20 after:bg-white after:rounded-full")

                            for i, num in enumerate(ROULETTE_ORDER):
                                color = "bg-red-400" if i % 2 == 1 else "bg-black"
                                if i == 0:
                                    color = "bg-green-800"
                                ui.label(str(num)).classes(f"absolute font-bold origin-bottom h-1/2 left-1/2 -translate-x-1/2 {color} text-white text-center [clip-path:polygon(0_0,100%_0,50%_100%)] pt-4").style(f"width: 31px; transform: rotate({i * cell_size}deg);")

                        with ui.element("div").classes("flex gap-2 justify-center items-center mt-5"):
                            spin_btn = ui.button("Spin", on_click=lambda: self.event_bus.notify(RouletteCommandRequest.SPIN_WHEEL, self.spin_wheel_cmd)).classes("size-20 transition-colors duration-200 bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 disabled:cursor-not-allowed disabled:opacity-50 rounded-lg")
                            spin_btn.bind_enabled_from(self, "spin_wheel_cmd")
                            
                            end_game_btn = ui.button("End Game", on_click=lambda: self.event_bus.notify(RouletteCommandRequest.END_GAME, self.end_game_cmd)).classes("transition-colors duration-200 bg-red-5 hover:bg-red-6 text-white font-bold py-2 px-4 disabled:cursor-not-allowed disabled:opacity-50 rounded-lg")
                            end_game_btn.bind_enabled_from(self, "end_game_cmd")

                        self.winning_bets_display = ui.label("Payout: $0").classes("font-bold text-lg")

                if not self.bets_table:
                    self.bets_table = ui.element("div").classes("relative bg-white p-10 rounded-t-lg shadow-lg grid gap-0.5 grid-rows-14 grid-cols-5")

                outside_bets_style = "writing-mode: sideways-lr;"
                outside_bets_classes = "text-center bg-gray-600 text-white p-2 text-md font-bold select-none flex justify-center items-center relative"

                number_bets_classes = "text-center text-white p-2 text-md font-bold select-none relative"
                buttons_classes = "bg-blue-6 disabled:bg-transparent! transition-opacity duration-200 opacity-0 hover:opacity-50"

                # Build the actual bets table
                with self.bets_table:
                    # 1. The Green "0" Header (Row 1)
                    zero_classes = "text-center bg-green-800 text-white p-2 text-md font-bold select-none col-span-3 col-start-3 row-start-1 rounded-t-4xl flex justify-center items-center"
                    zero_button = ui.label("0").classes(f"{zero_classes} relative")
                    with zero_button:
                        straight_bet = bets.StraightBet(number=0)
                        ui.button(on_click=lambda bet=straight_bet: self.place_bet(bet)).classes(f"{zero_classes} {buttons_classes} absolute inset-0 w-full h-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[straight_bet.key] = self.create_chip(straight_bet).on_click(lambda bet=straight_bet: self.place_bet(bet))

                        for i in range(1, 4):
                            split_bet_right = bets.SplitBet(numbers=(0, i))
                            ui.button(on_click=lambda bet=split_bet_right: self.place_bet(bet)).classes(f"{buttons_classes} absolute -bottom-1 left-{i-1}/3 p-0 min-h-0 h-2 w-1/3 transition-opacity duration-300 cursor-pointer z-10").bind_enabled_from(self, "can_place_bet")
                            self.chips[split_bet_right.key] = self.create_chip(split_bet_right).on_click(lambda bet=split_bet_right: self.place_bet(bet)).classes(f"-bottom-3 left-{2*i-1}/6 -translate-x-1/2 z-20")

                        for i in range(2):
                            street_bet = bets.StreetBet(numbers=(0, i+1, i+2))
                            ui.button(on_click=lambda bet=street_bet: self.place_bet(bet)).classes(f"{buttons_classes} absolute -bottom-2 left-{i+1}/3 -translate-x-1/2 p-0 min-h-0 size-3 transition-opacity duration-300 cursor-pointer z-10").bind_enabled_from(self, "can_place_bet")
                            self.chips[street_bet.key] = self.create_chip(street_bet).on_click(lambda bet=street_bet: self.place_bet(bet)).classes(f"-bottom-3 left-{i+1}/3 -translate-x-1/2 z-20")

                    # 2. Outside Bets (Columns 1 & 2, explicitly mapped to rows)
                    low_bet_button = ui.label("1 to 18").classes(f"{outside_bets_classes} col-start-1 row-start-2 row-span-2").style(outside_bets_style)
                    with low_bet_button:
                        low_bet = bets.HighLowBet(is_high=False)
                        ui.button(on_click=lambda: self.place_bet(low_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[low_bet.key] = self.create_chip(low_bet).on_click(lambda: self.place_bet(low_bet)).style("writing-mode: horizontal-tb;")
                    
                    first_12_button = ui.label("1st 12").classes(f"{outside_bets_classes} col-start-2 row-start-2 row-span-4").style(outside_bets_style)
                    with first_12_button:
                        first_12_bet = bets.DozenBet(dozen=1)
                        ui.button(on_click=lambda: self.place_bet(first_12_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[first_12_bet.key] = self.create_chip(first_12_bet).on_click(lambda: self.place_bet(first_12_bet)).style("writing-mode: horizontal-tb;")

                    even_bet_button = ui.label("EVEN").classes(f"{outside_bets_classes} col-start-1 row-start-4 row-span-2").style(outside_bets_style)
                    with even_bet_button:
                        even_bet = bets.OddEvenBet(is_odd=False)
                        ui.button(on_click=lambda: self.place_bet(even_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[even_bet.key] = self.create_chip(even_bet).on_click(lambda: self.place_bet(even_bet)).style("writing-mode: horizontal-tb;")

                    red_bet_button = ui.label("RED").classes(f"{outside_bets_classes} col-start-1 row-start-6 row-span-2 bg-red-6").style(outside_bets_style)
                    with red_bet_button:
                        red_bet = bets.ColorBet(color=bets.Color.RED)
                        ui.button(on_click=lambda: self.place_bet(red_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[red_bet.key] = self.create_chip(red_bet).on_click(lambda: self.place_bet(red_bet)).style("writing-mode: horizontal-tb;")

                    second_12_button = ui.label("2nd 12").classes(f"{outside_bets_classes} col-start-2 row-start-6 row-span-4").style(outside_bets_style)
                    with second_12_button:
                        second_12_bet = bets.DozenBet(dozen=2)
                        ui.button(on_click=lambda: self.place_bet(second_12_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[second_12_bet.key] = self.create_chip(second_12_bet).on_click(lambda: self.place_bet(second_12_bet)).style("writing-mode: horizontal-tb;")

                    black_bet_button = ui.label("BLACK").classes(f"{outside_bets_classes} col-start-1 row-start-8 row-span-2 bg-black").style(outside_bets_style)
                    with black_bet_button:
                        black_bet = bets.ColorBet(color=bets.Color.BLACK)
                        ui.button(on_click=lambda: self.place_bet(black_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[black_bet.key] = self.create_chip(black_bet).on_click(lambda: self.place_bet(black_bet)).style("writing-mode: horizontal-tb;")

                    odd_bet_button = ui.label("ODD").classes(f"{outside_bets_classes} col-start-1 row-start-10 row-span-2").style(outside_bets_style)
                    with odd_bet_button:
                        odd_bet = bets.OddEvenBet(is_odd=True)
                        ui.button(on_click=lambda: self.place_bet(odd_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[odd_bet.key] = self.create_chip(odd_bet).on_click(lambda: self.place_bet(odd_bet)).style("writing-mode: horizontal-tb;")

                    third_12_button = ui.label("3rd 12").classes(f"{outside_bets_classes} col-start-2 row-start-10 row-span-4").style(outside_bets_style)
                    with third_12_button:
                        third_12_bet = bets.DozenBet(dozen=3)
                        ui.button(on_click=lambda: self.place_bet(third_12_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[third_12_bet.key] = self.create_chip(third_12_bet).on_click(lambda: self.place_bet(third_12_bet)).style("writing-mode: horizontal-tb;")

                    high_bet_button = ui.label("19 to 36").classes(f"{outside_bets_classes} col-start-1 row-start-12 row-span-2").style(outside_bets_style)
                    with high_bet_button:
                        high_bet = bets.HighLowBet(is_high=True)
                        ui.button(on_click=lambda: self.place_bet(high_bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                        self.chips[high_bet.key] = self.create_chip(high_bet).on_click(lambda: self.place_bet(high_bet)).style("writing-mode: horizontal-tb;")

                    # 3. Main Numbers Loop (Columns 3, 4, 5)
                    for i in range(1, 37):
                        # Calculate exact grid coordinates dynamically
                        row = ((i - 1) // 3) + 2  # Starts at row 2 because row 1 is '0'
                        col = ((i - 1) % 3) + 3   # Starts at col 3 because cols 1 & 2 are outside bets
                        
                        color = RouletteRenderer.determine_color(i)
                        number_button = ui.label(str(i)).classes(f"{number_bets_classes} {color} col-start-{col} row-start-{row} num-{i}")

                        with number_button:
                            straight_bet = bets.StraightBet(number=i)
                            ui.button(on_click=lambda bet=straight_bet: self.place_bet(bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                            self.chips[straight_bet.key] = self.create_chip(straight_bet).on_click(lambda bet=straight_bet: self.place_bet(bet)).classes("z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2")

                            split_bet_right = bets.SplitBet(numbers=(i, i + 1)) if col < 5 else None
                            if split_bet_right:
                                ui.button(on_click=lambda bet=split_bet_right: self.place_bet(bet)).classes(f"{buttons_classes} absolute -right-1.5 top-0 h-full p-0 min-h-0 w-2 z-20").bind_enabled_from(self, "can_place_bet")
                                self.chips[split_bet_right.key] = self.create_chip(split_bet_right).on_click(lambda bet=split_bet_right: self.place_bet(bet)).classes("-right-3 top-1/2 -translate-y-1/2 z-20")
                            else:
                                street_bet = bets.StreetBet(numbers=(i- 2, i - 1, i))
                                ui.button(on_click=lambda bet=street_bet: self.place_bet(bet)).classes(f"{buttons_classes} absolute -right-1.5 top-0 h-full w-2 p-0 z-20").bind_enabled_from(self, "can_place_bet")
                                self.chips[street_bet.key] = self.create_chip(street_bet).on_click(lambda bet=street_bet: self.place_bet(bet)).classes("-right-3 top-1/2 -translate-y-1/2 z-30")

                                if row <= 12:
                                    line_bet = bets.LineBet(numbers=(i - 2, i - 1, i, i + 1, i + 2, i + 3))
                                    ui.button(on_click=lambda bet=line_bet: self.place_bet(bet)).classes(f"{buttons_classes} absolute -right-1.5 -bottom-2 size-4 min-h-0 p-0 z-20").bind_enabled_from(self, "can_place_bet")
                                    self.chips[line_bet.key] = self.create_chip(line_bet).on_click(lambda bet=line_bet: self.place_bet(bet)).classes("-right-3 -bottom-3 z-30")

                            split_bet_bottom = bets.SplitBet(numbers=(i, i + 3)) if row <= 12 else None
                            if split_bet_bottom:
                                ui.button(on_click=lambda bet=split_bet_bottom: self.place_bet(bet)).classes(f"{buttons_classes} absolute -bottom-1.5 left-0 w-full p-0 min-h-0 h-2 transition-opacity duration-300 cursor-pointer z-20").bind_enabled_from(self, "can_place_bet")
                                self.chips[split_bet_bottom.key] = self.create_chip(split_bet_bottom).on_click(lambda bet=split_bet_bottom: self.place_bet(bet)).classes("-bottom-3 left-1/2 -translate-x-1/2 z-20")

                            if row <= 12 and col < 5:
                                corner_bet = bets.CornerBet(numbers=(i, i + 1, i + 3, i + 4))
                                ui.button(on_click=lambda bet=corner_bet: self.place_bet(bet)).classes(f"{buttons_classes} absolute -bottom-2 -right-2 size-4 p-0 min-h-0 z-30").bind_enabled_from(self, "can_place_bet")
                                self.chips[corner_bet.key] = self.create_chip(corner_bet).on_click(lambda bet=corner_bet: self.place_bet(bet)).classes("-bottom-3 -right-3 z-30")

                    # 4. Column Bets (Row 14)
                    for c in range(3):
                        col = c + 3
                        col_bet_button = ui.label("2 to 1").classes(f"{number_bets_classes} bg-gray-600 col-start-{col} row-start-14")

                        with col_bet_button:
                            column_bet = bets.ColumnBet(column=c + 1)
                            ui.button(on_click=lambda bet=column_bet: self.place_bet(bet)).classes(f"{buttons_classes} absolute inset-0 size-full").bind_enabled_from(self, "can_place_bet")
                            self.chips[column_bet.key] = self.create_chip(column_bet).on_click(lambda bet=column_bet: self.place_bet(bet)).classes("z-10 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2")

                    self.funds_display = ui.label("Funds: $0").classes("absolute top-2 left-2 m-4 font-bold text-lg")
                    bet_input = ui.element("div").classes("flex flex-col-reverse items-center absolute bottom-0 left-0 pl-4 w-30")

                    with bet_input:
                        self.bet_slider = ui.slider(min=1, max=100, value=1, step=1).props("label: Bet Amount").classes("w-full")
                        self.bet_number = ui.number("Bet Amount", min=1, max=100).classes("font-bold w-full").bind_value(self.bet_slider, "value")
    
                    self.total_bet_display = ui.label("Total Bet: $0").classes("absolute bottom-0 right-2 font-bold text-lg")

    def place_bet(self, bet: bets.RouletteBet):
        """Places a bet on the table. The player must have sufficient funds to cover the bet amount, and the bet will be added to any existing bet of the same type on the table."""
        bet.bet = self.bet_number.value

        cmd = self.place_bet_cmd
        cmd.parameters[0].value = bet

        self.event_bus.notify(RouletteCommandRequest.PLACE_BET, cmd)

    def remove_bet(self, bet: bets.RouletteBet):
        """Removes a bet from the table."""
        cmd = self.remove_bet_cmd
        cmd.parameters[0].value = bet

        self.event_bus.notify(RouletteCommandRequest.REMOVE_BET, cmd)

    def create_chip(self, bet: bets.RouletteBet) -> ui.button:
        """Creates a chip button that can be used to place bets on the table."""
        chip = ui.button().classes("absolute text-sm min-h-0 p-1 m-0 rounded-full hidden opacity-0 transition-opacity duration-300 cursor-pointer")
        with chip:
            (
                ui.button("x")
                .classes("absolute -top-2 -right-2 leading-none p-1 m-0 min-h-0 text-sm bg-red-6 transition-color rounded-full duration-200 opacity-40 hover:opacity-100 disabled:cursor-not-allowed")
                .on("click", lambda: self.remove_bet(bet))
                .on("click", js_handler="(e) => { e.stopPropagation(); }")
            ).bind_enabled_from(self, "can_place_bet")
        chip.bind_enabled_from(self, "can_place_bet")
        return chip

    def on_bet(self, snapshot: RouletteSnapshot):
        for key, bet in snapshot.bets.items():
            chip = self.chips.get(key)
            if chip:
                chip.classes("opacity-100! block!").style("display: block;")
            else:
                chip = self.create_chip(bet)
                self.chips[key] = chip
                chip.classes("opacity-100! block!").style("display: block;")
            
            if bet.bet <= 0:
                chip.classes(remove="opacity-100! block!")
            else:
                chip.set_text(f"${bet.bet}")

        # Remove chips for bets that have been cleared
        cleared_bets = set(self.chips.keys()) - set(snapshot.bets.keys())
        for key in cleared_bets:
            chip = self.chips[key]
            chip.classes(remove="opacity-100! block!")

    async def clear_bets(self, _: RouletteSnapshot):
        """Clears all bets from the table."""

        await self.spin_signal.wait()  # Wait for any ongoing spin to complete
        for chip in self.chips.values():
            chip.classes(remove="opacity-100! block!")

    async def on_spin_result(self, snapshot: RouletteSnapshot):
        self.can_place_bet = False
        self.end_game_cmd = None  # Disable the end game button until the spin is complete
        self.spin_wheel_cmd = None  # Disable the spin button until the spin is complete
        self.spin_signal.clear()

        degrees_per_cell = 360 / len(ROULETTE_ORDER)
        landing_index = ROULETTE_ORDER.index(snapshot.landing_cell.number)

        DEGREES_PER_SECOND = 360

        # 1. Figure out where the wheel is currently pointing (0 to 359 degrees)
        current_offset = self.current_rotation % 360
        
        # 2. Figure out where it needs to point
        new_offset = landing_index * degrees_per_cell

        # 3. Calculate how many degrees forward it takes to reach the new offset
        if new_offset >= current_offset:
            distance_to_target = new_offset - current_offset
        else:
            # If the target is behind us, we have to wrap around the 360-degree mark
            distance_to_target = 360 - current_offset + new_offset

        # 4. Add the base spins and the calculated distance to the current rotation
        spin_count = random.randint(10, 15)
        target_rotation = self.current_rotation + (spin_count * 360) + distance_to_target

        time = target_rotation / DEGREES_PER_SECOND

        self.wheel.style(f"transition: transform {time}s ease-out; transform: rotate({-target_rotation}deg);")

        await asyncio.sleep(time)
        self.current_rotation = target_rotation

        self.winning_bets_display.set_text(f"Payout: ${sum(bet.earnings() for bet in snapshot.payouts)}")

        self.spin_signal.set()
        self.can_place_bet = True

    @staticmethod
    def determine_color(num: int) -> str:
        """Determines the color of a roulette number based on its position in the ROULETTE_ORDER list."""
        idx = ROULETTE_ORDER.index(num)

        if idx == 0:
            return "bg-green-800"
        return "bg-red-400" if idx % 2 == 1 else "bg-black"

    async def setup_commands(self, snapshot: RouletteSnapshot):
        """Sets up the command schema for placing bets, which will be used to notify the event bus when a bet is placed."""

        await self.spin_signal.wait()  # Wait for any ongoing spin to complete

        self.place_bet_cmd = snapshot.available_commands.get(RouletteCommandRequest.PLACE_BET)
        self.clear_bets_cmd = snapshot.available_commands.get(RouletteCommandRequest.CLEAR_BETS)
        self.remove_bet_cmd = snapshot.available_commands.get(RouletteCommandRequest.REMOVE_BET)
        self.spin_wheel_cmd = snapshot.available_commands.get(RouletteCommandRequest.SPIN_WHEEL)
        self.end_game_cmd = snapshot.available_commands.get(RouletteCommandRequest.END_GAME)

        total_bet = sum(bet.bet for bet in snapshot.bets.values())
        self.bet_slider._props["max"] = snapshot.active_player.funds - total_bet
        self.bet_number._props["max"] = snapshot.active_player.funds - total_bet
        self.funds_display.set_text(f"Funds: ${snapshot.active_player.funds}")
        self.total_bet_display.set_text(f"Total Bet: ${total_bet}")
