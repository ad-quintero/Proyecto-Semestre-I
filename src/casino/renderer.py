from typing import Callable, Literal
from nicegui import ui
from utils.renderer import Renderer
from utils import audio

class CasinoRenderer:
    """The main renderer for the casino, responsible for rendering the main menu and handling game selection."""
    
    def __init__(self, on_game_selected: Callable[[Literal["Blackjack", "Poker", "Slot Machine", "Roulette"]], None]):
        self.on_game_selected = on_game_selected

        self.container = ui.element('div').classes('fixed inset-0')
        self.audio: ui.audio | None = None
        self.showed_intro: bool = False

    def build_ui(self, game_to_render: Renderer = None):
        ui.add_css(
            """         
            .intro {
                z-index: 20;
                background-color: #1b0047;
                animation: 8s ease-out forwards fadeOut;
                overflow: hidden;
                position: absolute;
                inset: 0;
                // display: none;

                &:after {
                    content: "";
                    position: absolute;
                    width: 100%;
                    height: 33.3%;
                    bottom: 0;
                    background-image: linear-gradient(to bottom, #8070b7, transparent);
                    z-index: -10;
                }
            }

            @keyframes fadeOut {
                0% { opacity: 1; }
                80% { opacity: 1; }
                99% { height: 100% }
                100% { opacity: 0; height: 0; }
            }
            """
        )

        with ui.element("div"):
            self.audio = audio.play_audio("casino/bg_music.mp3", True).classes("bg-music")
            ui.run_javascript('''
                document.getElementsByClassName("bg-music")[0].volume = 0.3;
            ''')

        self.container.clear()
        with self.container:
            if not self.showed_intro:
                with ui.element('div').classes('absolute inset-0 flex items-center justify-center intro'):
                    ui.image("assets/images/laptop.png").classes("w-1/2 h-auto")

                    with ui.column().classes('items-center justify-center gap-4'):
                        ui.label("Bienvenido").classes("text-6xl font-bold text-white w-fit mx-auto font-serif")
                        ui.image("assets/images/logo.svg").classes("w-full h-auto")
                        ui.label("Online").classes("text-6xl p-2 rounded-sm text-white bg-pink-700 w-fit mx-auto font-serif")
                self.showed_intro = True

            if game_to_render is not None:
                game_to_render.build_ui()
            else:
                with ui.element('div').classes('size-full flex items-center justify-around bg-[#1b0047]'):
                    with ui.grid(rows=2, columns=2,).classes('gap-8'):
                        for name, icon_path in [("Blackjack", "assets/images/blackjack.jpg"),
                                                ("Poker", "assets/images/poker.jpg"),
                                                ("Slot Machine", "assets/images/slot_machine.jpg"),
                                                ("Roulette", "assets/images/roulette.jpg")]:
                            btn = ui.element("button").classes("size-90 flex flex-col group relative cursor-pointer").on("click", lambda n=name: self.on_game_selected(n))
                            with btn:
                                ui.image(icon_path).classes("object-fill absolute inset-0 w-full h-full rounded-lg")
                                ui.label(name).classes("absolute bottom-0 h-3/10 w-full text-center text-white text-4xl bg-zinc-800 font-serif flex justify-center items-center border-3 border-black group-hover:bg-zinc-800/50 group-hover:h-full transition-all duration-300")

                    with ui.column().classes("gap-10 max-w-1/3 flex flex-col items-center justify-center"):
                        ui.image("assets/images/logo.svg").classes("w-full h-auto")
                        ui.label("Juega con nosotros. ¡La suerte está de tu lado!").classes("text-5xl text-white font-serif leading-20")
