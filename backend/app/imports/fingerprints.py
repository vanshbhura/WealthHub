import hashlib
from typing import Any, Optional
from datetime import datetime, date


def generate_transaction_fingerprint(
    user_id: Any,
    platform_id: Any,
    transaction_date: Any,
    transaction_type: str,
    amount: float | str,
    asset_identifier: Optional[str] = None,
    quantity: Optional[float | str] = None,
    price: Optional[float | str] = None,
    reference_id: Optional[str] = None,
) -> str:
    """
    Generates a deterministic SHA256 canonical hash of the transaction attributes.
    Ensures identical transactions produce identical fingerprints across imports.
    """
    # Normalize date to YYYY-MM-DD
    if isinstance(transaction_date, (datetime, date)):
        date_str = transaction_date.strftime("%Y-%m-%d")
    elif isinstance(transaction_date, str):
        date_str = transaction_date.strip()[:10]
    else:
        date_str = str(transaction_date or "")

    # Normalize float / Decimal values to 4 decimal places
    def _norm_num(val: Any) -> str:
        if val is None or val == "":
            return ""
        try:
            return f"{float(val):.4f}"
        except (ValueError, TypeError):
            return str(val).strip()

    amt_str = _norm_num(amount)
    qty_str = _norm_num(quantity)
    prc_str = _norm_num(price)
    type_str = str(transaction_type or "").strip().upper()
    asset_str = str(asset_identifier or "").strip().upper()
    ref_str = str(reference_id or "").strip()

    canonical_parts = [
        str(user_id),
        str(platform_id),
        date_str,
        type_str,
        amt_str,
        qty_str,
        prc_str,
        asset_str,
        ref_str,
    ]

    canonical_payload = "|".join(canonical_parts)
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
