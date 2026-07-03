from casino.casino import Casino
from nicegui import ui as gui


@gui.page("/")
async def main():
    casino = Casino("Python Casino")
    await casino.menu()

if __name__ in {"__main__", "__mp_main__"}:
    gui.run()
