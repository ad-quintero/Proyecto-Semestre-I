from abc import ABC
from typing import Type
from casino.games import Game
from casino.player import PlayerAccount, PlayerController, PlayerBuyIn
from utils.commands.command_manager import CommandManager
from utils.event_listener import EventBus
from utils.renderer import Renderer


class GameManager:
    """The Base Template for all games."""

    def __init__(
        self,
        game: Type[Game],
        player: PlayerAccount,
        renderer: Type[Renderer],
        player_buy_in: PlayerBuyIn,
    ):
        self.event_bus = EventBus()
        self.game = game(self.event_bus, player_buy_in)
        self.command_manager = CommandManager(self.game)
        self.player = PlayerController(self.event_bus, self.command_manager, player.id)
        self.renderer = renderer(self.event_bus)
