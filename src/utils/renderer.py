from abc import ABC, abstractmethod
from utils.event_listener import EventBus


class Renderer(ABC):
    """
    A class responsible for rendering the game. This is just a default implementation,
    and specific games must override this with their own rendering logic.

    Any class inheriting from Renderer must subscribe to game events in the __init__ method and implement the render method to update the game display based on the current game state.
    """

    event_bus: EventBus

    @abstractmethod
    def __init__(self, event_bus: EventBus):
        """Initializes the renderer and subscribes to relevant game events."""
        self.event_bus = event_bus

    def build_ui(self):
        """Builds the initial UI components. This can be overridden by specific game renderers if needed."""
        raise NotImplementedError("build_ui method must be implemented by the specific game renderer.")
