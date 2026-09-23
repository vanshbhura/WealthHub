from typing import Dict, List, Any
from app.imports.enums import ImportType

# Canonical normalized field definitions
NORMALIZED_FIELDS = [
    {"name": "date", "label": "Transaction Date", "required": True, "description": "Date of the transaction"},
    {"name": "transaction_type", "label": "Transaction Type", "required": False, "description": "BUY, SELL, DEPOSIT, WITHDRAWAL, etc."},
    {"name": "description", "label": "Description", "required": False, "description": "Transaction remarks or particulars"},
    {"name": "asset_name", "label": "Asset Name", "required": False, "description": "Full name of stock, mutual fund, or asset"},
    {"name": "symbol", "label": "Symbol / Ticker", "required": False, "description": "Trading symbol (e.g., RELIANCE, INFY)"},
    {"name": "isin", "label": "ISIN", "required": False, "description": "International Securities Identification Number"},
    {"name": "quantity", "label": "Quantity / Units", "required": False, "description": "Number of shares or units"},
    {"name": "price", "label": "Price / NAV", "required": False, "description": "Execution price or unit NAV"},
    {"name": "amount", "label": "Amount", "required": False, "description": "Total transaction amount"},
    {"name": "debit", "label": "Debit", "required": False, "description": "Debit / Withdrawal amount (banks)"},
    {"name": "credit", "label": "Credit", "required": False, "description": "Credit / Deposit amount (banks)"},
    {"name": "fees", "label": "Fees / Charges", "required": False, "description": "Brokerage and platform charges"},
    {"name": "taxes", "label": "Taxes", "required": False, "description": "STT, GST, Stamp Duty"},
    {"name": "net_amount", "label": "Net Amount", "required": False, "description": "Net amount settlement"},
    {"name": "account_number", "label": "Account / Folio", "required": False, "description": "Demat, account, or folio number"},
    {"name": "transaction_id", "label": "Transaction ID", "required": False, "description": "Unique provider transaction identifier"},
    {"name": "order_id", "label": "Order ID", "required": False, "description": "Broker order number"},
    {"name": "reference_id", "label": "Reference / UTR", "required": False, "description": "Bank reference or UTR"},
    {"name": "balance", "label": "Running Balance", "required": False, "description": "Post-transaction account balance"},
    {"name": "currency", "label": "Currency", "required": False, "description": "Transaction currency (default INR)"},
]

# Field alias dictionaries for auto-mapping
FIELD_ALIASES: Dict[str, List[str]] = {
    "date": [
        "date", "trade date", "transaction date", "txn date", "value date",
        "trans date", "booking date", "execution date", "order date"
    ],
    "transaction_type": [
        "type", "transaction type", "txn type", "trade type", "buy/sell",
        "action", "side", "order type", "trans type", "activity"
    ],
    "description": [
        "description", "particulars", "narration", "remarks", "details",
        "transaction details", "notes", "memo"
    ],
    "asset_name": [
        "asset", "asset name", "security", "security name", "scrip name",
        "instrument", "scheme name", "scheme", "fund name", "company"
    ],
    "symbol": [
        "symbol", "ticker", "scrip", "stock", "stock symbol", "trading symbol",
        "equity symbol"
    ],
    "isin": [
        "isin", "isin number", "isin code", "security isin"
    ],
    "quantity": [
        "quantity", "qty", "units", "shares", "no. of shares", "traded qty",
        "executed qty", "allotted units"
    ],
    "price": [
        "price", "rate", "trade price", "avg price", "execution price",
        "nav", "unit price", "cost per share"
    ],
    "amount": [
        "amount", "trade value", "total amount", "gross amount", "total",
        "txn amount", "transaction amount", "value"
    ],
    "debit": [
        "debit", "withdrawal", "dr", "debit amount", "withdrawal amount", "withdrawals"
    ],
    "credit": [
        "credit", "deposit", "cr", "credit amount", "deposit amount", "deposits"
    ],
    "fees": [
        "fees", "brokerage", "charges", "commission", "platform fee",
        "other charges", "total charges"
    ],
    "taxes": [
        "taxes", "tax", "stt", "gst", "stamp duty", "sebi turnover fee"
    ],
    "net_amount": [
        "net amount", "net value", "net total", "settlement amount", "net pay-in/pay-out"
    ],
    "account_number": [
        "account", "account number", "account no", "demat account", "demat no",
        "folio", "folio number", "folio no", "client id"
    ],
    "transaction_id": [
        "transaction id", "txn id", "trade id", "trans id", "trade no",
        "deal id", "contract note no"
    ],
    "order_id": [
        "order id", "order no", "exchange order no"
    ],
    "reference_id": [
        "reference id", "ref no", "reference number", "utr", "cheque no", "chq no"
    ],
    "balance": [
        "balance", "closing balance", "available balance", "running balance"
    ],
    "currency": [
        "currency", "curr"
    ],
}
