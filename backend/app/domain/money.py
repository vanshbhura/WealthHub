from typing import Optional, Union
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation


class Money:
    """Represents monetary amounts with currency and safe decimal operations."""
    DEFAULT_CURRENCY = "INR"

    def __init__(self, amount: Union[float, int, str, Decimal] = 0, currency: str = DEFAULT_CURRENCY):
        if isinstance(amount, Decimal):
            self._amount = amount
        else:
            try:
                self._amount = Decimal(str(amount))
            except (InvalidOperation, ValueError, TypeError):
                self._amount = Decimal("0")
        self.currency = (currency or self.DEFAULT_CURRENCY).upper()

    @property
    def amount(self) -> float:
        return float(self._amount)

    @property
    def decimal_amount(self) -> Decimal:
        return self._amount

    def round_to(self, decimals: int = 2) -> float:
        quantize_str = "0." + "0" * decimals if decimals > 0 else "1"
        return float(self._amount.quantize(Decimal(quantize_str), rounding=ROUND_HALF_UP))

    def __repr__(self) -> str:
        return f"Money({self.amount}, '{self.currency}')"


def safe_div(
    numerator: Optional[Union[float, int, Decimal]],
    denominator: Optional[Union[float, int, Decimal]],
    default: Optional[float] = None
) -> Optional[float]:
    """Safe division preventing ZeroDivisionError, NaN, and Inf."""
    if numerator is None or denominator is None:
        return default
    try:
        num = float(numerator)
        den = float(denominator)
        if abs(den) < 1e-9:
            return default
        return num / den
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def safe_round(value: Optional[Union[float, int, Decimal]], decimals: int = 2) -> Optional[float]:
    """Rounds float/decimal safely, preserving None."""
    if value is None:
        return None
    try:
        return round(float(value), decimals)
    except (ValueError, TypeError):
        return None


def calculate_percentage_change(
    current: Optional[Union[float, int]],
    previous: Optional[Union[float, int]]
) -> Optional[float]:
    """Calculates percentage change = ((current - previous) / previous) * 100."""
    if current is None or previous is None:
        return None
    try:
        cur = float(current)
        prev = float(previous)
        if abs(prev) < 1e-9:
            return None
        return ((cur - prev) / prev) * 100.0
    except (ValueError, TypeError):
        return None
