from casino.casino import Casino
from nicegui import ui as gui, app


@gui.page("/")
async def main():
    casino = Casino("Python Casino")
    await casino.menu()

if __name__ in {"__main__", "__mp_main__"}:
    app.add_static_files("/assets", "assets")
    gui.run()
