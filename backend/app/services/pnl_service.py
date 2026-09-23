from typing import Optional, Tuple
from app.domain.calculations import calculate_pnl
from app.domain.money import safe_round


class PnlService:
    @staticmethod
    def calculate(
        current_value: Optional[float],
        invested_value: Optional[float]
    ) -> Tuple[float, Optional[float]]:
        """
        Calculates absolute profit/loss and return percentage.
        When invested_value == 0, returns (pnl, None) per financial normalization rules.
        """
        pnl, pnl_pct = calculate_pnl(current_value, invested_value)
        return round(pnl, 2), safe_round(pnl_pct, 2)
