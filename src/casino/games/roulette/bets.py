from dataclasses import dataclass

from typing import TYPE_CHECKING, Union

from casino.games.roulette.cells import Color, RouletteCell

@dataclass(kw_only=True)
class RouletteBet:
    """Represents a bet placed by a player on the roulette table."""
    bet: float = 0
    payout: int = 0 # Payout multiplier (e.g., 35 for a straight bet, 1 for red/black)

    def validate(self):
        raise NotImplementedError("Subclasses must implement validate method to ensure bet parameters are valid.")

    def earnings(self) -> float:
        """Calculates the potential earnings from this bet."""
        return self.bet * (self.payout + 1)  # +1 to include the original bet in the payout
    
    @property
    def key(self) -> str:
        """A unique key representing the bet, used for tracking and comparison."""
        raise NotImplementedError("Subclasses must implement key property to provide a unique identifier for the bet.")

@dataclass(kw_only=True)
class StraightBet(RouletteBet):
    """Bet on a single number."""
    number: int
    payout: int = 35 # 35:1

    def validate(self):
        if not (0 <= self.number <= 36):
            raise ValueError(f"Invalid number for Straight Bet: {self.number}. Must be between 0 and 36 inclusive.")

    @property
    def key(self) -> str:
        return f"Straight-{self.number}"

    def __str__(self):
        return f"Straight Bet on {self.number} with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class SplitBet(RouletteBet):
    """Bet on two adjacent numbers."""
    numbers: tuple[int, int]
    payout: int = 17 # 17:1

    def validate(self):
        if not all(0 <= n <= 36 for n in self.numbers):
            raise ValueError(f"Invalid numbers for Split Bet: {self.numbers}. All numbers must be between 0 and 36 inclusive.")

    @property
    def key(self) -> str:
        return f"Split-{self.numbers}"

    def __str__(self):
        return f"Split Bet on {self.numbers} with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class StreetBet(RouletteBet):
    """Bet on three numbers in a row."""
    numbers: tuple[int, int, int]
    payout: int = 11 # 11:1

    def validate(self):
        if not all(0 <= n <= 36 for n in self.numbers):
            raise ValueError(f"Invalid numbers for Street Bet: {self.numbers}. All numbers must be between 0 and 36 inclusive.")

    @property
    def key(self) -> str:
        return f"Street-{self.numbers}"

    def __str__(self):
        return f"Street Bet on {self.numbers} with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class CornerBet(RouletteBet):
    """Bet on four numbers that meet at a corner."""
    numbers: tuple[int, int, int, int]
    payout: int = 8 # 8:1

    def validate(self):
        if not all(0 <= n <= 36 for n in self.numbers):
            raise ValueError(f"Invalid numbers for Corner Bet: {self.numbers}. All numbers must be between 0 and 36 inclusive.")

    @property
    def key(self) -> str:
        return f"Corner-{self.numbers}"

    def __str__(self):
        return f"Corner Bet on {self.numbers} with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class LineBet(RouletteBet):
    """Bet on six numbers in two adjacent rows."""
    numbers: tuple[int, int, int, int, int, int]
    payout: int = 5 # 5:1

    def validate(self):
        if not all(0 <= n <= 36 for n in self.numbers):
            raise ValueError(f"Invalid numbers for Line Bet: {self.numbers}. All numbers must be between 0 and 36 inclusive.")

    @property
    def key(self) -> str:
        return f"Line-{self.numbers}"

    def __str__(self):
        return f"Line Bet on {self.numbers} with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class DozenBet(RouletteBet):
    """
    Bet on 12 numbers (1-12, 13-24, 25-36).

    1 for 1-12, 2 for 13-24, 3 for 25-36
    """
    dozen: int
    payout: int = 2 # 2:1

    def validate(self):
        if self.dozen not in (1, 2, 3):
            raise ValueError(f"Invalid dozen for Dozen Bet: {self.dozen}. Must be 1 (1-12), 2 (13-24), or 3 (25-36).")

    @property
    def key(self) -> str:
        return f"Dozen-{self.dozen}"

    def __str__(self):
        return f"Dozen Bet on {self.dozen} ({'1-12' if self.dozen == 1 else '13-24' if self.dozen == 2 else '25-36'}) with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class ColumnBet(RouletteBet):
    """
    Bet on 12 numbers in a vertical column.
    1 for first column (1,4,7,...34), 2 for second column (2,5,8,...35), 3 for third column (3,6,9,...36)
    """
    column: int
    payout: int = 2 # 2:1

    def validate(self):
        if self.column not in (1, 2, 3):
            raise ValueError(f"Invalid column for Column Bet: {self.column}. Must be 1 (first column), 2 (second column), or 3 (third column).")

    @property
    def key(self) -> str:
        return f"Column-{self.column}"

    def __str__(self):
        return f"Column Bet on {"1st" if self.column == 1 else "2nd" if self.column == 2 else "3rd"} column with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class ColorBet(RouletteBet):
    """Bet on red or black."""
    color: Color
    payout: int = 1 # 1:1

    def validate(self):
        if self.color not in (Color.RED, Color.BLACK):
            raise ValueError(f"Invalid color for Color Bet: {self.color}. Must be RED or BLACK.")

    @property
    def key(self) -> str:
        return f"Color-{self.color}"

    def __str__(self):
        return f"Color Bet on {self.color} with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class OddEvenBet(RouletteBet):
    """Bet on odd or even numbers."""
    is_odd: bool
    payout: int = 1 # 1:1

    def validate(self):
        if not isinstance(self.is_odd, bool):
            raise ValueError(f"Invalid is_odd for OddEvenBet: {self.is_odd}. Must be a boolean.")

    @property
    def key(self) -> str:
        return f"OddEven-{self.is_odd}"

    def __str__(self):
        return f"Odd/Even Bet on {'Odd' if self.is_odd else 'Even'} with bet {self.bet} and payout {self.payout}"

@dataclass(kw_only=True)
class HighLowBet(RouletteBet):
    """Bet on low (1-18) or high (19-36) numbers."""
    is_high: bool
    payout: int = 1 # 1:1

    def validate(self):
        if not isinstance(self.is_high, bool):
            raise ValueError(f"Invalid is_high for HighLowBet: {self.is_high}. Must be a boolean.")

    @property
    def key(self) -> str:
        return f"HighLow-{self.is_high}"

    def __str__(self):
        return f"High/Low Bet on {'High (19-36)' if self.is_high else 'Low (1-18)'} with bet {self.bet} and payout {self.payout}"

RouletteBet = Union[
    StraightBet,
    SplitBet,
    StreetBet,
    CornerBet,
    LineBet,
    DozenBet,
    ColumnBet,
    ColorBet,
    OddEvenBet,
    HighLowBet
]

def is_winning_bet(bet: RouletteBet, cell: RouletteCell) -> bool:
    """
        Determines if a given bet wins based on the roulette cell outcome.
        # Parameters

        - bet (RouletteBet): The bet placed by the player.
        - cell (RouletteCell or tuple[RouletteCell, RouletteCell]): The outcome of the roulette spin.
        A single cell if the ball lands in a single pocket, or a tuple of two cells if the ball lands on the edge between two pockets.
    """

    if isinstance(bet, StraightBet):
        return cell.number == bet.number
    elif isinstance(bet, SplitBet):
        return cell.number in bet.numbers
    elif isinstance(bet, StreetBet):
        return cell.number in bet.numbers
    elif isinstance(bet, CornerBet):
        return cell.number in bet.numbers
    elif isinstance(bet, LineBet):
        return cell.number in bet.numbers
    elif isinstance(bet, DozenBet):
        if bet.dozen == 1:
            return 1 <= cell.number <= 12
        elif bet.dozen == 2:
            return 13 <= cell.number <= 24
        elif bet.dozen == 3:
            return 25 <= cell.number <= 36
    elif isinstance(bet, ColumnBet):
        if bet.column == 1:
            return cell.number % 3 == 1
        elif bet.column == 2:
            return cell.number % 3 == 2
        elif bet.column == 3:
            return cell.number % 3 == 0 and cell.number != 0
    elif isinstance(bet, ColorBet):
        return cell.color == bet.color
    elif isinstance(bet, OddEvenBet):
        if cell.number == 0:
            return False
        return (cell.number % 2 != 0) if bet.is_odd else (cell.number % 2 == 0)
    elif isinstance(bet, HighLowBet):
        if cell.number == 0:
            return False
        return (cell.number >= 19) if bet.is_high else (cell.number <= 18)
    
    raise ValueError(f"Unknown bet type: {type(bet)}")

def bet_from_string(bet_str: str) -> RouletteBet:
    """
    Parses a bet from a string representation. This is a placeholder implementation and should be expanded to handle all bet types and formats.

    - Straight: "Straight 17 50" for a $50 bet on number 17
    - Split: "Split 17-20 30" for a $30 bet on the edge between 17 and 20
    - Street: "Street 1-3 25" for a $25 bet on the row containing numbers 1, 2, and 3
    - Corner: "Corner 1-2-4-5 20" for a $20 bet on the square containing numbers 1, 2, 4, and 5
    - Line: "Line 1-6 15" for a $15 bet on the two rows containing numbers 1-6
    - Dozen: "Dozen 1 100" for a $100 bet on the first dozen (1-12)
    - Column: "Column 2 50" for a $50 bet on the second column (2,5,8,...35)
    - Color: "Color Red 100" for a $100 bet on red
    - Odd/Even: "OddEven Odd 50" for a $50 bet on odd numbers
    - High/Low: "HighLow High 25" for a $25 bet on high numbers (19-36)
    """

    bet_str = bet_str.strip().lower()

    if bet_str.startswith("straight"):
        _, number, bet = bet_str.split()
        return StraightBet(number=int(number), bet=float(bet))
    elif bet_str.startswith("split"):
        _, numbers, bet = bet_str.split()
        num1, num2 = map(int, numbers.split('-'))
        return SplitBet(numbers=(num1, num2), bet=float(bet))
    elif bet_str.startswith("street"):
        _, numbers, bet = bet_str.split()
        num1, num2, num3 = map(int, numbers.split('-'))
        return StreetBet(numbers=(num1, num2, num3), bet=float(bet))
    elif bet_str.startswith("corner"):
        _, numbers, bet = bet_str.split()
        num1, num2, num3, num4 = map(int, numbers.split('-'))
        return CornerBet(numbers=(num1, num2, num3, num4), bet=float(bet))
    elif bet_str.startswith("line"):
        _, numbers, bet = bet_str.split()
        num1, num2, num3, num4, num5, num6 = map(int, numbers.split('-'))
        return LineBet(numbers=(num1, num2, num3, num4, num5, num6), bet=float(bet))
    elif bet_str.startswith("dozen"):
        _, dozen, bet = bet_str.split()
        return DozenBet(dozen=int(dozen), bet=float(bet))
    elif bet_str.startswith("column"):
        _, column, bet = bet_str.split()
        return ColumnBet(column=int(column), bet=float(bet))
    elif bet_str.startswith("color"):
        _, color, bet = bet_str.split()
        color_enum = Color.RED if color.lower() == "red" else Color.BLACK
        return ColorBet(color=color_enum, bet=float(bet))
    elif bet_str.startswith("oddeven"):
        _, odd_even, bet = bet_str.split()
        is_odd = odd_even.lower() == "odd"
        return OddEvenBet(is_odd=is_odd, bet=float(bet))
    elif bet_str.startswith("highlow"):
        _, high_low, bet = bet_str.split()
        is_high = high_low.lower() == "high"
        return HighLowBet(is_high=is_high, bet=float(bet))
    
    raise ValueError(f"Unknown bet format: {bet_str}")
