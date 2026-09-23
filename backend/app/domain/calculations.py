from typing import Optional, Tuple, Dict, Any
from app.domain.money import safe_div, safe_round


def calculate_pnl(
    current_value: Optional[float],
    invested_value: Optional[float]
) -> Tuple[float, Optional[float]]:
    """
    Computes absolute profit/loss and profit/loss percentage.
    If invested_value == 0, returns (pnl, None) to avoid division by zero or misleading return %.
    """
    cur = float(current_value) if current_value is not None else 0.0
    inv = float(invested_value) if invested_value is not None else 0.0
    pnl = cur - inv

    if abs(inv) < 1e-9:
        return pnl, None

    pnl_pct = (pnl / inv) * 100.0
    return pnl, pnl_pct


def calculate_daily_movement(
    current_total: Optional[float],
    previous_snapshot_total: Optional[float]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Computes daily movement comparing current portfolio to previous snapshot.
    Returns (None, None) when no valid previous snapshot exists.
    """
    if current_total is None or previous_snapshot_total is None:
        return None, None

    prev = float(previous_snapshot_total)
    cur = float(current_total)

    if prev <= 0:
        return None, None

    change = cur - prev
    change_pct = (change / prev) * 100.0
    return change, change_pct


def calculate_quantity_valuation(
    quantity: float,
    current_price: float,
    average_buy_price: float = 0.0,
    reported_invested: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculates valuation for quantity-based assets (Stocks, ETFs, Mutual Funds, Crypto).
    """
    qty = max(0.0, float(quantity or 0.0))
    cp = max(0.0, float(current_price or 0.0))
    abp = max(0.0, float(average_buy_price or 0.0))

    if reported_invested is not None and reported_invested > 0:
        invested = float(reported_invested)
    else:
        invested = qty * abp

    current_val = qty * cp if cp > 0 else invested
    pnl, pnl_pct = calculate_pnl(current_val, invested)

    return {
        "quantity": qty,
        "average_buy_price": abp,
        "invested_value": invested,
        "current_price": cp,
        "current_value": current_val,
        "profit_loss": pnl,
        "profit_loss_percentage": pnl_pct
    }


def calculate_precious_metal_valuation(
    quantity_in_grams: float,
    current_price_per_gram: float,
    average_buy_price_per_gram: float = 0.0,
    reported_invested: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculates quantity-based precious metal valuation (Gold, Silver, SGB).
    """
    qty = max(0.0, float(quantity_in_grams or 0.0))
    cp = max(0.0, float(current_price_per_gram or 0.0))
    abp = max(0.0, float(average_buy_price_per_gram or 0.0))

    if reported_invested is not None and reported_invested > 0:
        invested = float(reported_invested)
    else:
        invested = qty * abp

    current_val = qty * cp if cp > 0 else invested
    pnl, pnl_pct = calculate_pnl(current_val, invested)

    return {
        "quantity": qty,
        "average_buy_price": abp,
        "invested_value": invested,
        "current_price": cp,
        "current_value": current_val,
        "profit_loss": pnl,
        "profit_loss_percentage": pnl_pct
    }


def calculate_p2p_position(
    principal_invested: float,
    principal_outstanding: Optional[float] = None,
    interest_earned: Optional[float] = None,
    interest_received: Optional[float] = None,
    repayments: Optional[float] = None,
    overdue_amount: Optional[float] = None,
    write_offs: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculates P2P lending position metrics.
    Does not fabricate write-offs or repayments if provider doesn't supply them.
    """
    p_inv = max(0.0, float(principal_invested or 0.0))
    p_out = float(principal_outstanding) if principal_outstanding is not None else p_inv
    int_earned = float(interest_earned) if interest_earned is not None else 0.0
    int_rec = float(interest_received) if interest_received is not None else 0.0
    rep = float(repayments) if repayments is not None else 0.0
    overdue = float(overdue_amount) if overdue_amount is not None else None
    loss = float(write_offs) if write_offs is not None else 0.0

    # Current exposure = principal outstanding - confirmed write-offs
    current_value = max(0.0, p_out - loss)
    # Total net earnings = interest earned (or received) - write-offs
    pnl = (int_earned if int_earned > 0 else int_rec) - loss
    invested_basis = p_inv if p_inv > 0 else current_value
    pnl_pct = (pnl / invested_basis) * 100.0 if invested_basis > 0 else None

    return {
        "principal_invested": p_inv,
        "principal_outstanding": p_out,
        "interest_earned": interest_earned,
        "interest_received": interest_received,
        "repayments": repayments,
        "overdue_amount": overdue,
        "write_offs": write_offs,
        "current_value": current_value,
        "invested_value": invested_basis,
        "profit_loss": pnl,
        "profit_loss_percentage": pnl_pct
    }
