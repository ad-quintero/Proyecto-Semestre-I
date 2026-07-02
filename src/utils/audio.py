from nicegui import ui
import os, random

def play_random_sound_from_directory(directory: str):
    """
    Play a random sound file from the specified directory.
    """
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return

    sound_files = [f for f in os.listdir(directory) if f.endswith(('.mp3', '.wav', '.ogg'))]
    
    if not sound_files:
        print(f"No sound files found in {directory}.")
        return

    random_sound = random.choice(sound_files)
    sound_path = os.path.join(directory, random_sound)
    
    # Use NiceGUI to play the sound
    audio = ui.audio(src=sound_path, autoplay=True).classes("size-0 opacity-0")
    audio.on("ended", lambda: audio.delete())  # Remove the audio element after it finishes playing

def play_audio(file_path: str, loop: bool = False):
    """
    Play an audio file using NiceGUI. Starting directory will be assets/sfx/. The file_path should be relative to that directory, e.g., "blackjack/card1.mp3".
    """

    absolute_path = os.path.join("assets", "sfx", file_path)
    if not os.path.exists(absolute_path):
        print(f"Audio file {file_path} does not exist.")
        return

    # Use NiceGUI to play the sound
    audio = ui.audio(src=absolute_path, autoplay=True, loop=loop).classes("size-0 opacity-0")
    audio.on("ended", lambda: audio.delete())  # Remove the audio element after it finishes playing

    return audio
