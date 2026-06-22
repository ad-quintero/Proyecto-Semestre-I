from enum import Enum
from nicegui import ui

class ChipValue(Enum):
    ONE = 1
    FIVE = 5
    TEN = 10
    TWENTY_FIVE = 25
    FIFTY = 50
    ONE_HUNDRED = 100
    FIVE_HUNDRED = 500
    ONE_THOUSAND = 1000

class ChipUI:
    def __init__(self, value: ChipValue):
        self.value = value

        from nicegui import ui

        # Define the custom CSS styles for the chip elements
        CHIP_STYLE = f'''
            width: 5em;
            aspect-ratio: 1;
            border-radius: 50%;
            background: conic-gradient(
                {self.get_color()} 0deg 15deg,   #ffffff 15deg 30deg,
                {self.get_color()} 30deg 45deg,  #ffffff 45deg 60deg,
                {self.get_color()} 60deg 75deg,  #ffffff 75deg 90deg,
                {self.get_color()} 90deg 105deg, #ffffff 105deg 120deg,
                {self.get_color()} 120deg 135deg,#ffffff 135deg 150deg,
                {self.get_color()} 150deg 165deg,#ffffff 165deg 180deg,
                {self.get_color()} 180deg 195deg,#ffffff 195deg 210deg,
                {self.get_color()} 225deg,#ffffff 225deg 240deg,
                {self.get_color()} 240deg 255deg,#ffffff 255deg 270deg,
                {self.get_color()} 270deg 285deg,#ffffff 285deg 300deg,
                {self.get_color()} 300deg 315deg,#ffffff 315deg 330deg,
                {self.get_color()} 330deg 345deg,#ffffff 345deg 360deg
            );
            box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 8px 16px rgba(0,0,0,0.3);
        '''

        INNER_DISC_STYLE = '''
            width: 75%;
            height: 75%;
            border-radius: 50%;
            background-color: #0d47a1;
            border: 4px dashed rgba(255, 255, 255, 0.4);
            box-shadow: inset 0 4px 10px rgba(0,0,0,0.4);
        '''
 
        # The Outer Poker Chip
        with ui.element('div').style(CHIP_STYLE).classes('flex items-center justify-center'):
            # The Inner Disc
            with ui.element('div').style(INNER_DISC_STYLE).classes('flex items-center justify-center'):
                # The Denomination Text
                ui.label(f'${self.value.value}').classes('text-white font-black select-none').style('text-shadow: 0 2px 4px rgba(0,0,0,0.5);')
    
    def get_color(self):
        colors = {
            ChipValue.ONE: '#007bff',
            ChipValue.FIVE: '#28a745',
            ChipValue.TEN: '#ffc107',
            ChipValue.TWENTY_FIVE: '#dc3545',
            ChipValue.FIFTY: '#6f42c1',
            ChipValue.ONE_HUNDRED: '#fd7e14',
            ChipValue.FIVE_HUNDRED: '#20c997',
            ChipValue.ONE_THOUSAND: '#6610f2'
        }
        return colors[self.value]
