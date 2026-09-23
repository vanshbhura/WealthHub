from datetime import date
from app.services.xirr_service import XirrService


def test_xirr_prompt_spec_example():
    """
    Test the exact example specified in Prompt 3 Section 15:
    2025-01-01: -100000
    2025-06-01: -50000
    2026-01-01: -25000
    2026-09-20: +190000
    """
    cash_flows = [
        (date(2025, 1, 1), -100000.0),
        (date(2025, 6, 1), -50000.0),
        (date(2026, 1, 1), -25000.0),
        (date(2026, 9, 20), 190000.0),
    ]
    xirr = XirrService.calculate_xirr(cash_flows)
    assert xirr is not None
    # Annualized return mathematically calculated is 5.79%
    assert 5.5 <= xirr <= 6.5
    assert round(xirr, 2) == 5.79


def test_xirr_one_year_simple_growth():
    """Invest 100,000 on Jan 1, end with 115,000 exactly 1 year later (15.0% return)."""
    cash_flows = [
        (date(2025, 1, 1), -100000.0),
        (date(2026, 1, 1), 115000.0),
    ]
    xirr = XirrService.calculate_xirr(cash_flows)
    assert xirr is not None
    assert abs(xirr - 15.0) < 0.2


def test_xirr_with_intermediate_withdrawals():
    """Invest 100k, withdraw 20k, then end with 95k."""
    cash_flows = [
        (date(2024, 1, 1), -100000.0),
        (date(2024, 7, 1), 20000.0),   # Withdrawal
        (date(2025, 1, 1), 95000.0),   # Current portfolio value
    ]
    xirr = XirrService.calculate_xirr(cash_flows)
    assert xirr is not None
    assert xirr > 0.0


def test_xirr_edge_cases_invalid():
    """Edge cases returning None."""
    # Less than 2 cash flows
    assert XirrService.calculate_xirr([]) is None
    assert XirrService.calculate_xirr([(date(2025, 1, 1), -10000.0)]) is None

    # All negative (only investments, no terminal value)
    assert XirrService.calculate_xirr([
        (date(2025, 1, 1), -10000.0),
        (date(2025, 6, 1), -5000.0),
    ]) is None

    # All positive (no initial investment)
    assert XirrService.calculate_xirr([
        (date(2025, 1, 1), 10000.0),
        (date(2025, 6, 1), 5000.0),
    ]) is None

    # Same date (0 days difference)
    assert XirrService.calculate_xirr([
        (date(2025, 1, 1), -10000.0),
        (date(2025, 1, 1), 12000.0),
    ]) is None
