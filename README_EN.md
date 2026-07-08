# UMA Casino

Developed as the final project for the first semester of programming at Universidad Monteavila (March-July 2026) under the guidance of Professor Ernesto Lugo.

# Architecture

- **Main Language:** Python 3.14.6
- **Secondary Languages:** HTML, CSS, JavaScript
- **Main Development Platform:** Arch Linux (kernel 7.0.14-arch1-1)
- **External Libraries:** Pytest, NiceGUI

This project focuses on an object-oriented programming architecture. Each game, player, card, and piece is a unique class with specific functionality. Additionally, for effective communication between different system components, an event-driven programming model is used, where one system can subscribe to specific events from another system to react accordingly.

**RECOMMENDATION:** Don't analyze the rendering code. Python isn't made for GUI development. The interface is held together by sheer willpower and the universe's divine intervention.

# How to Run

1. Clone this repository.
2. Create and activate a virtual environment.
    - **Windows (PowerShell):** `python -m venv venv; .\venv\Scripts\activate.ps1`
    - **Windows (cmd):** `python -m venv venv && .\venv\Scripts\activate.bat`
    - **Linux and macOS:** `python3 -m venv venv && source venv/bin/activate`
3. Install dependencies `pip install -r requirements.txt`
4. Install this project as a dependency `pip install .`. Run with the _editable_ argument if you want to make changes to the code `pip install -e .`.
5. Run `python main.py`.

**Warning:** Due to security and privacy reasons, modern browsers [disallow audio autoplay](https://developer.mozilla.org/en-US/docs/Web/Media/Guides/Autoplay). In order to play the site's background music it must be manually authorized.
