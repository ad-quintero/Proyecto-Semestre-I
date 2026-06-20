from casino.games.generic_events import GenericEvent
from casino.games.poker.phases import PokerPhase
from utils.event_listener import EventBus
from utils.renderer import Renderer
from .poker import PokerSnapshot
from .events import PokerEvent


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
