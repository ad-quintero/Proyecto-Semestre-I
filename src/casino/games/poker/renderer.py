from casino.games.generic_events import GenericEvent
from utils.event_listener import EventBus
from utils.renderer import Renderer
from .poker import PokerSnapshot
from .events import PokerEvent
from .events import PokerCommandRequest
from ui.models.card import CardUI
from utils.cards import CardView
from utils.commands.command import CommandSchema
from utils import audio

from nicegui import ui
from dataclasses import dataclass
import asyncio

class PokerTerminalRenderer(Renderer):
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)

        self.event_bus.subscribe(GenericEvent.GAME_START, self.render_available_commands)
        self.event_bus.subscribe(PokerEvent.TURN, self.render_available_commands)
        self.event_bus.subscribe(PokerEvent.CARD_HELD, self.render_hand)
        self.event_bus.subscribe(PokerEvent.CARDS_DISCARDED, self.render_hand)
        self.event_bus.subscribe(PokerEvent.DEAL_CARDS, self.render_hand)

        self.event_bus.subscribe(PokerEvent.HAND_OVER, self.render_hand_over)

    def render_hand(self, snapshot: PokerSnapshot):
        """Renders the active player's hand. If hide_hand is True, it will not show the cards during the dealing process."""

        for card in snapshot.community_cards:
            print(f"Your hand: {str(card.card)} (held: {card.hold})")


    def render_available_commands(self, snapshot: PokerSnapshot):
        print(f"Available commands ({snapshot.active_player.funds}$ available){f" ({snapshot.bet}$ bet)" if snapshot.bet else ""}:")
        for idx, command in enumerate(snapshot.available_commands, start=1):
            print(f"{idx}. {command.display_name}")

    def render_hand_over(self, snapshot: PokerSnapshot):
        if snapshot.final_hand:
            hand_rank, cards = snapshot.final_hand
            print(f"Hand over! Your hand: {hand_rank.name} with {', '.join(str(card) for card in cards)}. You {'won' if snapshot.payout_multiplier and snapshot.payout_multiplier > 0 else 'lost'} {snapshot.bet * snapshot.payout_multiplier if snapshot.payout_multiplier else snapshot.bet}$." )
        else:
            print("Hand over! You tied or lost, better luck next time!")


poker_positions = {
    "cards": "absolute top-1/2 left-2/5",
    "deck": "absolute top-1/10 left-4/5 rotate-45",
}

@dataclass
class BetButton:
    bet_amount: int
    button: ui.button
    enabled: bool

@dataclass
class CardElement:
    card: ui.element
    label: ui.label
    hold: bool

class PokerRenderer(Renderer):
    def __init__(self, event_bus):
        super().__init__(event_bus)

        self.event_bus.subscribe(PokerEvent.TURN, self.setup_commands)
        self.event_bus.subscribe(PokerEvent.DEAL_CARDS, self.deal_cards)
        self.event_bus.subscribe(PokerEvent.BET_CHANGE, self.change_bet)
        self.event_bus.subscribe(PokerEvent.CARD_HELD, self.held_card)
        self.event_bus.subscribe(PokerEvent.CARDS_DISCARDED, self.discarded_cards)
        self.event_bus.subscribe(PokerEvent.HAND_OVER, self.hand_over)
        self.event_bus.subscribe(PokerEvent.HAND_RESET, self.reset_ui)

        self.container: ui.element | None = None
        self.game_area: ui.element | None = None
        self.buttons_area: ui.element | None = None

        self.bet_buttons: dict[int, BetButton] = {}  # Dictionary to hold BetButton instances
        self.cards_container: ui.element = None
        self.cards: list[CardElement] = []

        self.discard_cards_cmd: CommandSchema | None = None
        self.end_cmd: CommandSchema | None = None
        self.hold_card_cmd: CommandSchema | None = None
        self.place_bet_cmd: CommandSchema | None = None
        self.start_cmd: CommandSchema | None = None
        self.new_hand_cmd: CommandSchema | None = None

        self.bet = 0
        self.can_place_bet = True

        self.discarding_signal = asyncio.Event()
        self.discarding_signal.set()

    def build_ui(self):
        if not self.container:
            self.container = ui.element('div').classes('relative size-full flex flex-col game-container bg-emerald-700')

        with self.container:
            if not self.game_area:
                self.game_area = ui.element("div").classes('relative grow')
            with self.game_area:
                deck = ui.element("div").classes(f"{poker_positions['deck']} w-16 h-24 bg-gray-500 rounded-lg shadow-lg pointer-events-none")

                with deck:
                    CardUI(card=CardView())

            if not self.buttons_area:
                self.buttons_area = ui.column().classes('gap-2 gap-y-10 items-center pb-50 pt-10 bg-cyan-900 shadow-2xl')
            with self.buttons_area:
                with ui.row().classes("gap-10 text-white text-lg"):
                    self.player_funds_label = ui.label("Player funds: 0$")
                    ui.label("Bet: 0$").bind_text_from(self, "bet", backward=lambda f: f"Bet: {f}$")

                with ui.row().classes('gap-2'):    
                    for bet_amount in [1, 5, 10, 25, 50, 100, 500, 1000]:
                        with ui.column():
                            button_classes = 'disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out'
                            button_add = ui.button(f"+{bet_amount}$", on_click=lambda bet=bet_amount: self.place_bet(bet)).classes(f"{button_classes} bg-green-5 hover:bg-green-6")
                            button_remove = ui.button(f"-{bet_amount}$", on_click=lambda bet=bet_amount: self.place_bet(-bet)).classes(f"{button_classes} bg-red-5 hover:bg-red-6")
                            self.bet_buttons[bet_amount] = BetButton(bet_amount=bet_amount, button=button_add, enabled=True)
                            self.bet_buttons[-bet_amount] = BetButton(bet_amount=-bet_amount, button=button_remove, enabled=True)

                with ui.row().classes('gap-2'):
                    self.discard_button = ui.button("Discard", on_click=lambda: self.event_bus.notify(PokerCommandRequest.DISCARD_CARDS, self.discard_cards_cmd)).classes('bg-blue-5 hover:bg-blue-6 disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out')
                    self.discard_button.bind_enabled_from(self, "discard_cards_cmd")

                    self.start_button = ui.button("Start Hand", on_click=lambda: self.event_bus.notify(PokerCommandRequest.NEW_HAND, self.start_cmd)).classes('bg-blue-5 hover:bg-blue-6 disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out')
                    self.start_button.bind_enabled_from(self, "start_cmd")

                    self.end_button = ui.button("End Game", on_click=lambda: self.event_bus.notify(PokerCommandRequest.END_GAME, self.end_cmd)).classes('bg-gray-5 hover:bg-gray-6 disabled:brightness-50 disabled:cursor-not-allowed transition-colors duration-150 ease-in-out')
                    self.end_button.bind_enabled_from(self, "end_cmd")
    
    def reset_ui(self, _snapshot: PokerSnapshot):
        self.bet = 0
        self.can_place_bet = True
        self.cards.clear()
        self.game_area.clear()
        self.buttons_area.clear()

        self.build_ui()

    def place_bet(self, amount: int):
        if self.place_bet_cmd:
            with self.container:
                audio.play_audio("casino/button.mp3")
            cmd = self.place_bet_cmd
            cmd.parameters[0].value = amount
            self.event_bus.notify(PokerCommandRequest.CHANGE_BET, cmd)

    def change_bet(self, snapshot: PokerSnapshot):
        self.bet = snapshot.bet
        self.player_funds_label.text = f"Player funds: ${snapshot.active_player.funds}"

    async def deal_cards(self, snapshot: PokerSnapshot):
        cards = snapshot.community_cards
        self.can_place_bet = False
        self.setup_commands(snapshot) # Disable bet buttons

        with self.game_area:
            for idx, card_view in enumerate(cards):
                    card_elem = ui.element("button").classes(f"{poker_positions['deck']} transition-all duration-200 ease-in-out bg-transparent p-0 flex flex-col items-center justify-center gap-2")

                    with card_elem:
                        card_view.card.is_face_up = False
                        card = CardUI(card=card_view.card)

                        label = ui.label("Held")
                        label.classes("transition-opacity duration-200 ease-in-out text-sm text-gray-700 opacity-0")
                        self.cards.append(CardElement(card=card_elem, label=label, hold=False))
                        audio.play_random_sound_from_directory("assets/sfx/card")

                    await asyncio.sleep(0.01)

                    card_elem.classes(remove=poker_positions['deck'], add=f"{poker_positions['cards']} translate-x-[{idx * 115}%] rotate-0")
                    
                    await asyncio.sleep(0.2)
                    
                    await card.flip()

                    def hold_card(idx: int):
                        if self.hold_card_cmd:
                            cmd = self.hold_card_cmd
                            cmd.parameters[0].value = idx
                            self.event_bus.notify(PokerCommandRequest.HOLD_CARD, cmd)

                    card_elem.classes("cursor-pointer")
                    card_elem.on("click", lambda idx=idx: hold_card(idx))

    def held_card(self, snapshot: PokerSnapshot):
        with self.container:
            audio.play_audio("poker/hold_card.mp3")

        for idx, card_view in enumerate(snapshot.community_cards):
            if card_view.hold:
                card = self.cards[idx]
                card.label.classes("opacity-100")
                card.card.classes("-translate-y-5")
                card.hold = True

                card.card.props("disable").classes("pointer-events-none")
            else:
                self.cards[idx].label.classes("opacity-0")

    async def discarded_cards(self, snapshot: PokerSnapshot):
        discarded_indices = []

        self.discarding_signal.clear()  # Indicate that discarding is in progress

        for idx, card in enumerate(self.cards):
            with self.container:
                audio.play_random_sound_from_directory("assets/sfx/card")

            if not card.hold:
                card.label.classes("opacity-0")
                card.card.classes("-translate-y-200").props("disable")
    
                discarded_indices.append(idx)
                await asyncio.sleep(0.1)
        
        with self.game_area:
            for idx, card_view in enumerate(snapshot.community_cards):
                    if idx not in discarded_indices:
                        continue
                    
                    card_elem = ui.element("button").classes(f"{poker_positions['deck']} transition-all duration-200 ease-in-out bg-transparent p-0 flex flex-col items-center justify-center gap-2")

                    with card_elem:
                        audio.play_random_sound_from_directory("assets/sfx/card")

                        card_view.card.is_face_up = False
                        card = CardUI(card=card_view.card)

                        label = ui.label("Held")
                        label.classes("transition-opacity duration-200 ease-in-out text-sm text-gray-700 opacity-0")
                        self.cards[idx] = CardElement(card=card_elem, label=label, hold=False)

                    await asyncio.sleep(0.01)

                    card_elem.classes(remove=poker_positions['deck'], add=f"{poker_positions['cards']} translate-x-[{idx * 115}%] rotate-0")

                    await asyncio.sleep(0.2)
                    
                    await card.flip()
        
        self.held_card(snapshot)
        await asyncio.sleep(1)
        self.discarding_signal.set()

    async def hand_over(self, snapshot: PokerSnapshot):
        await self.discarding_signal.wait()  # Wait for any ongoing discarding process to finish
        if snapshot.payout_multiplier and snapshot.payout_multiplier > 0:
            with self.container:
                audio.play_audio("casino/win.mp3")
            self._show_end_modal(f"You won {snapshot.bet * snapshot.payout_multiplier}$!")
        else:
            with self.container:
                audio.play_audio("casino/lose.mp3")
            self._show_end_modal(f"You lost {snapshot.bet}$! Better luck next time.")

    def _show_end_modal(self, msg: str):
        with self.container:
            dialog = ui.dialog(value=True).classes("w-1/3 absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2")

        async def reset_game():
            if self.new_hand_cmd:
                dialog.close()
                await asyncio.sleep(0.1)  # Ensure the dialog is closed before resetting the UI

                self.event_bus.notify(PokerCommandRequest.NEW_HAND, self.new_hand_cmd)

        def end_game():
            if self.end_cmd:
                self.event_bus.notify(PokerCommandRequest.END_GAME, self.end_cmd)
            dialog.close()

        with dialog:
            with ui.element("div").classes("flex flex-col items-center gap-4"):
                ui.label(msg).classes("text-3xl text-white font-bold mb-4")

                with ui.row().classes("justify-center gap-4"):
                    ui.button("Close", on_click=end_game)
                    ui.button("New Game", on_click=reset_game)

    def setup_commands(self, snapshot: PokerSnapshot):
        self.bet = snapshot.bet
        self.player_funds_label.set_text(f"Player Funds: ${snapshot.active_player.funds:.2f}")
        
        self.start_cmd = snapshot.available_commands.get(PokerCommandRequest.START_ROUND)
        self.end_cmd = snapshot.available_commands.get(PokerCommandRequest.END_GAME)
        self.discard_cards_cmd = snapshot.available_commands.get(PokerCommandRequest.DISCARD_CARDS)
        self.place_bet_cmd = snapshot.available_commands.get(PokerCommandRequest.CHANGE_BET)
        self.hold_card_cmd = snapshot.available_commands.get(PokerCommandRequest.HOLD_CARD)
        self.new_hand_cmd = snapshot.available_commands.get(PokerCommandRequest.NEW_HAND)

        self.player_funds_label.text = f"Player funds: ${snapshot.active_player.funds}"

        for bet_button in self.bet_buttons.values():
            bet_button.button.disable()

        for bet_button in self.bet_buttons.values():
            if bet_button.bet_amount > 0:
                # Enable "+" buttons if the player's total wallet can cover the increased bet
                can_afford = (self.bet + bet_button.bet_amount) <= snapshot.active_player.funds
                bet_button.button.set_enabled(can_afford and self.can_place_bet)
            elif bet_button.bet_amount < 0:
                # Enable "-" buttons only if lowering the bet doesn't drop the current bet below 0
                # (Remember: bet_button.bet_amount is negative here, like -10)
                can_lower = (self.bet + bet_button.bet_amount) >= 0
                bet_button.button.set_enabled(can_lower and self.can_place_bet)
