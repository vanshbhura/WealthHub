from typing import Optional, Tuple, List
from datetime import date
from app.domain.calculations import calculate_daily_movement
from app.domain.money import safe_round


class PerformanceService:
    @staticmethod
    def calculate_daily_change(
        current_total: Optional[float],
        previous_snapshot_total: Optional[float]
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculates today_change and today_change_percentage from previous snapshot.
        If no previous snapshot exists, returns (None, None).
        """
        change, change_pct = calculate_daily_movement(current_total, previous_snapshot_total)
        return safe_round(change, 2), safe_round(change_pct, 2)

    @staticmethod
    def calculate_period_return(
        start_value: float,
        end_value: float,
        start_date: date,
        end_date: date
    ) -> dict:
        """
        Calculates absolute period return, percentage return, and annualized CAGR.
        """
        if start_value <= 0:
            return {
                "absolute_return": round(end_value - start_value, 2),
                "percentage_return": None,
                "cagr": None,
                "days": (end_date - start_date).days
            }

        abs_ret = end_value - start_value
        pct_ret = (abs_ret / start_value) * 100.0
        days = max(1, (end_date - start_date).days)
        years = days / 365.0

        cagr = None
        if years >= 1.0 and end_value > 0 and start_value > 0:
            try:
                cagr = ((end_value / start_value) ** (1.0 / years) - 1.0) * 100.0
            except (ValueError, OverflowError):
                cagr = None

        return {
            "absolute_return": round(abs_ret, 2),
            "percentage_return": round(pct_ret, 2),
            "cagr": safe_round(cagr, 2),
            "days": days
        }
