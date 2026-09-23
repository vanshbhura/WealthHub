import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, Optional, Tuple, List
from app.imports.enums import ValidationSeverity, ImportType
from app.models.asset import AssetType
from app.models.transaction import TransactionType


DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%Y/%m/%d",
    "%d %b %Y",
    "%d-%b-%Y",
    "%d %B %Y",
    "%d-%B-%Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
]


class RowValidator:
    """
    Validates and normalizes single statement rows into canonical types.
    Enforces strict calendar validation, decimal money arithmetic,
    and asset category heuristics.
    """

    @staticmethod
    def parse_date(date_str: str) -> Tuple[Optional[datetime], Optional[str]]:
        """
        Parses date string against allowed formats.
        Returns (parsed_datetime, error_message).
        Strictly rejects impossible calendar dates like 31/02/2026.
        """
        if not date_str or not str(date_str).strip():
            return None, "Date is required."

        clean = str(date_str).strip().split(" ")[0]  # Take date part if date + time

        for fmt in DATE_FORMATS:
            try:
                dt = datetime.strptime(clean, fmt)
                # Ensure year is reasonable
                if dt.year < 1970 or dt.year > 2100:
                    return None, f"Year {dt.year} is out of realistic range (1970-2100)."
                return dt, None
            except ValueError:
                continue

        # Try full string with time
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                dt = datetime.strptime(str(date_str).strip(), fmt)
                return dt, None
            except ValueError:
                continue

        return None, f"Invalid date '{date_str}'. Expected formats: DD/MM/YYYY, DD-MM-YYYY, or YYYY-MM-DD."

    @staticmethod
    def parse_money(amount_str: Any) -> Tuple[Optional[Decimal], Optional[str]]:
        """
        Parses and cleans monetary amounts. Strips currency signs (₹, Rs), commas, and spaces.
        Returns (Decimal, error_message).
        """
        if amount_str is None or amount_str == "":
            return None, "Amount is empty."

        clean = str(amount_str).strip()
        # Remove currency symbols and formatting
        clean = re.sub(r"[₹\$\€\£]|rs\.?|inr", "", clean, flags=re.IGNORECASE).strip()
        clean = clean.replace(",", "").replace(" ", "")

        # Handle parentheses as negative: (100.50) -> -100.50
        if clean.startswith("(") and clean.endswith(")"):
            clean = "-" + clean[1:-1].strip()

        # Handle Dr / Cr suffixes
        is_dr = clean.lower().endswith("dr")
        is_cr = clean.lower().endswith("cr")
        if is_dr or is_cr:
            clean = clean[:-2].strip()

        try:
            val = Decimal(clean)
            if is_dr and val > 0:
                val = -val
            return val, None
        except (InvalidOperation, ValueError):
            return None, f"Amount '{amount_str}' is not a valid numeric amount."

    @staticmethod
    def parse_number(num_str: Any) -> Tuple[Optional[Decimal], Optional[str]]:
        """Parses floating-point or integer quantity/price without currency conversions."""
        if num_str is None or num_str == "":
            return None, None

        clean = str(num_str).strip().replace(",", "")
        try:
            return Decimal(clean), None
        except (InvalidOperation, ValueError):
            return None, f"Value '{num_str}' is not a valid number."

    @classmethod
    def infer_transaction_type(
        cls,
        raw_type: Optional[str],
        description: Optional[str],
        amount: Optional[Decimal],
        debit: Optional[Decimal],
        credit: Optional[Decimal],
    ) -> str:
        """Heuristically determines the canonical transaction type."""
        # Check debit/credit first
        if debit is not None and debit > 0:
            return TransactionType.WITHDRAWAL.value
        if credit is not None and credit > 0:
            return TransactionType.DEPOSIT.value

        combined = f"{raw_type or ''} {description or ''}".upper()

        if re.search(r"\b(BUY|PURCHASE|BOUGHT|ALLOTMENT|ALLOT|SIP)\b", combined):
            return TransactionType.BUY.value
        if re.search(r"\b(SELL|SOLD|REDEMPTION|REDEEM)\b", combined):
            return TransactionType.SELL.value
        if re.search(r"\b(DIVIDEND|DIV)\b", combined):
            return TransactionType.DIVIDEND.value
        if re.search(r"\b(INTEREST|INT\.? CR)\b", combined):
            return TransactionType.INTEREST.value
        if re.search(r"\b(TRANSFER IN|NEFT CR|RTGS CR|UPI CR|RECEIVED)\b", combined):
            return TransactionType.TRANSFER_IN.value
        if re.search(r"\b(TRANSFER OUT|NEFT DR|RTGS DR|UPI DR|SENT)\b", combined):
            return TransactionType.TRANSFER_OUT.value
        if re.search(r"\b(DEPOSIT|CREDIT)\b", combined):
            return TransactionType.DEPOSIT.value
        if re.search(r"\b(WITHDRAWAL|DEBIT)\b", combined):
            return TransactionType.WITHDRAWAL.value
        if re.search(r"\b(FEE|CHARGES|BROKERAGE|AMC)\b", combined):
            return TransactionType.FEE.value
        if re.search(r"\b(TAX|STT|GST|STAMP DUTY|TDS)\b", combined):
            return TransactionType.TAX.value

        # Amount sign heuristic
        if amount is not None:
            if amount < 0:
                return TransactionType.WITHDRAWAL.value
            elif amount > 0:
                return TransactionType.DEPOSIT.value

        return TransactionType.OTHER.value

    @classmethod
    def infer_asset_type(
        cls,
        import_type: str,
        asset_name: Optional[str],
        symbol: Optional[str],
        isin: Optional[str],
    ) -> str:
        """Determines asset category based on import type, security name, and symbol."""
        if import_type == ImportType.BANK.value:
            return AssetType.CASH.value
        if import_type == ImportType.DIGITAL_GOLD.value:
            return AssetType.DIGITAL_GOLD.value
        if import_type == ImportType.DIGITAL_SILVER.value:
            return AssetType.DIGITAL_SILVER.value
        if import_type == ImportType.P2P.value:
            return AssetType.P2P_LOANS.value

        combined = f"{asset_name or ''} {symbol or ''}".upper()

        if isin and isin.startswith("INF"):
            return AssetType.MUTUAL_FUNDS.value
        if re.search(r"\b(MUTUAL FUND|MF|GROWTH|DIRECT PLAN|REGULAR PLAN|INDEX FUND)\b", combined):
            return AssetType.MUTUAL_FUNDS.value
        if re.search(r"\b(ETF|BEES)\b", combined):
            return AssetType.ETFS.value
        if re.search(r"\b(GOLD)\b", combined):
            return AssetType.DIGITAL_GOLD.value
        if re.search(r"\b(SILVER)\b", combined):
            return AssetType.DIGITAL_SILVER.value
        if re.search(r"\b(BOND|NCD|SGB)\b", combined):
            return AssetType.BONDS.value
        if re.search(r"\b(FD|FIXED DEPOSIT)\b", combined):
            return AssetType.FIXED_DEPOSITS.value

        # Default for broker import is STOCKS
        if import_type == ImportType.BROKER.value:
            return AssetType.STOCKS.value

        return AssetType.OTHER.value

    @classmethod
    def validate_row(
        cls,
        mapped_row: Dict[str, Any],
        import_type: str,
        platform_name: str = "",
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Validates mapped row fields. Returns:
        - normalized_row: dict with typed fields
        - issues: list of { "row_number": int, "field": str, "severity": str, "message": str }
        """
        row_num = mapped_row.get("__row_number__", 0)
        issues: List[Dict[str, Any]] = []

        # 1. Date Validation (Required)
        raw_date = mapped_row.get("date")
        parsed_dt, date_err = cls.parse_date(raw_date)
        if date_err:
            issues.append({
                "row_number": row_num,
                "field": "date",
                "severity": ValidationSeverity.ERROR.value,
                "message": date_err,
            })

        # 2. Amount / Debit / Credit Validation
        raw_amount = mapped_row.get("amount")
        raw_debit = mapped_row.get("debit")
        raw_credit = mapped_row.get("credit")

        parsed_amount = None
        parsed_debit = None
        parsed_credit = None

        if raw_debit is not None and raw_debit != "":
            d_val, d_err = cls.parse_money(raw_debit)
            if d_err:
                issues.append({"row_number": row_num, "field": "debit", "severity": ValidationSeverity.ERROR.value, "message": d_err})
            else:
                parsed_debit = abs(d_val)

        if raw_credit is not None and raw_credit != "":
            c_val, c_err = cls.parse_money(raw_credit)
            if c_err:
                issues.append({"row_number": row_num, "field": "credit", "severity": ValidationSeverity.ERROR.value, "message": c_err})
            else:
                parsed_credit = abs(c_val)

        if raw_amount is not None and raw_amount != "":
            a_val, a_err = cls.parse_money(raw_amount)
            if a_err:
                issues.append({"row_number": row_num, "field": "amount", "severity": ValidationSeverity.ERROR.value, "message": a_err})
            else:
                parsed_amount = a_val
        elif parsed_debit is not None:
            parsed_amount = -parsed_debit
        elif parsed_credit is not None:
            parsed_amount = parsed_credit

        if parsed_amount is None and not any(i["severity"] == ValidationSeverity.ERROR.value for i in issues):
            issues.append({
                "row_number": row_num,
                "field": "amount",
                "severity": ValidationSeverity.ERROR.value,
                "message": "Transaction amount (or Debit/Credit) is missing or zero.",
            })

        # 3. Quantity & Price Validation
        raw_qty = mapped_row.get("quantity")
        parsed_qty = None
        if raw_qty is not None and raw_qty != "":
            q_val, q_err = cls.parse_number(raw_qty)
            if q_err:
                issues.append({"row_number": row_num, "field": "quantity", "severity": ValidationSeverity.WARNING.value, "message": q_err})
            else:
                parsed_qty = abs(q_val)

        raw_price = mapped_row.get("price")
        parsed_price = None
        if raw_price is not None and raw_price != "":
            p_val, p_err = cls.parse_money(raw_price)
            if p_err:
                issues.append({"row_number": row_num, "field": "price", "severity": ValidationSeverity.WARNING.value, "message": p_err})
            else:
                parsed_price = abs(p_val)

        # 4. Transaction Type Inference
        tx_type = cls.infer_transaction_type(
            raw_type=mapped_row.get("transaction_type"),
            description=mapped_row.get("description"),
            amount=parsed_amount,
            debit=parsed_debit,
            credit=parsed_credit,
        )

        if tx_type == TransactionType.OTHER.value and not mapped_row.get("transaction_type"):
            issues.append({
                "row_number": row_num,
                "field": "transaction_type",
                "severity": ValidationSeverity.WARNING.value,
                "message": "Transaction type could not be confidently identified; default assigned.",
            })

        # 5. Asset Identification
        asset_name = mapped_row.get("asset_name") or mapped_row.get("symbol") or mapped_row.get("description")
        if not asset_name:
            if import_type == ImportType.BANK.value:
                asset_name = f"{platform_name or 'Bank'} Savings"
            else:
                asset_name = f"{platform_name or 'Investment'} Holding"
                issues.append({
                    "row_number": row_num,
                    "field": "asset_name",
                    "severity": ValidationSeverity.WARNING.value,
                    "message": "Asset / symbol name was not found in statement; assigned default.",
                })

        symbol = mapped_row.get("symbol")
        isin = mapped_row.get("isin")
        asset_type = cls.infer_asset_type(
            import_type=import_type,
            asset_name=asset_name,
            symbol=symbol,
            isin=isin,
        )

        # 6. Transaction Identifier / Order ID
        tx_id = mapped_row.get("transaction_id") or mapped_row.get("order_id") or mapped_row.get("reference_id")
        if not tx_id:
            issues.append({
                "row_number": row_num,
                "field": "transaction_id",
                "severity": ValidationSeverity.INFO.value,
                "message": "No transaction ID found in row; canonical fingerprint will be used for deduplication.",
            })

        # Build normalized representation
        normalized_row = {
            "row_number": row_num,
            "date": parsed_dt.strftime("%Y-%m-%d") if parsed_dt else None,
            "transaction_type": tx_type,
            "asset_name": asset_name,
            "asset_type": asset_type,
            "symbol": symbol,
            "isin": isin,
            "quantity": float(parsed_qty) if parsed_qty is not None else None,
            "price": float(parsed_price) if parsed_price is not None else None,
            "amount": float(parsed_amount) if parsed_amount is not None else 0.0,
            "currency": mapped_row.get("currency", "INR").upper(),
            "transaction_id": tx_id,
            "description": mapped_row.get("description"),
            "account_number": mapped_row.get("account_number"),
            "is_valid": not any(i["severity"] == ValidationSeverity.ERROR.value for i in issues),
        }

        return normalized_row, issues
