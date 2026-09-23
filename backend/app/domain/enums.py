import enum
from typing import Optional


class AssetCategory(str, enum.Enum):
    STOCK = "STOCK"
    ETF = "ETF"
    MUTUAL_FUND = "MUTUAL_FUND"
    FD = "FD"
    RD = "RD"
    P2P = "P2P"
    DIGITAL_GOLD = "DIGITAL_GOLD"
    DIGITAL_SILVER = "DIGITAL_SILVER"
    CRYPTO = "CRYPTO"
    BOND = "BOND"
    SGB = "SGB"
    NPS = "NPS"
    EPF = "EPF"
    PPF = "PPF"
    PHYSICAL_GOLD = "PHYSICAL_GOLD"
    PHYSICAL_SILVER = "PHYSICAL_SILVER"
    REAL_ESTATE = "REAL_ESTATE"
    CASH = "CASH"
    OTHER = "OTHER"


class TransactionType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    FEE = "FEE"
    TAX = "TAX"
    REPAYMENT = "REPAYMENT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    OTHER = "OTHER"


class DataSource(str, enum.Enum):
    BROKER_API = "BROKER_API"
    AA = "AA"
    PROVIDER_API = "PROVIDER_API"
    CSV = "CSV"
    PDF = "PDF"
    MANUAL = "MANUAL"


class DataFreshnessStatus(str, enum.Enum):
    REALTIME = "REALTIME"
    RECENT = "RECENT"
    TODAY = "TODAY"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"


CATEGORY_ALIASES = {
    "STOCKS": AssetCategory.STOCK,
    "STOCK": AssetCategory.STOCK,
    "EQUITY": AssetCategory.STOCK,
    "EQUITIES": AssetCategory.STOCK,
    "ETFS": AssetCategory.ETF,
    "ETF": AssetCategory.ETF,
    "MUTUAL_FUNDS": AssetCategory.MUTUAL_FUND,
    "MUTUAL_FUND": AssetCategory.MUTUAL_FUND,
    "MF": AssetCategory.MUTUAL_FUND,
    "FIXED_DEPOSITS": AssetCategory.FD,
    "FIXED_DEPOSIT": AssetCategory.FD,
    "FD": AssetCategory.FD,
    "RECURRING_DEPOSITS": AssetCategory.RD,
    "RECURRING_DEPOSIT": AssetCategory.RD,
    "RD": AssetCategory.RD,
    "P2P_LOANS": AssetCategory.P2P,
    "P2P_LOAN": AssetCategory.P2P,
    "P2P": AssetCategory.P2P,
    "DIGITAL_GOLD": AssetCategory.DIGITAL_GOLD,
    "DIGITAL_SILVER": AssetCategory.DIGITAL_SILVER,
    "CRYPTO": AssetCategory.CRYPTO,
    "CRYPTOCURRENCY": AssetCategory.CRYPTO,
    "BONDS": AssetCategory.BOND,
    "BOND": AssetCategory.BOND,
    "SGB": AssetCategory.SGB,
    "SOVEREIGN_GOLD_BOND": AssetCategory.SGB,
    "NPS": AssetCategory.NPS,
    "EPF": AssetCategory.EPF,
    "PPF": AssetCategory.PPF,
    "PHYSICAL_GOLD": AssetCategory.PHYSICAL_GOLD,
    "PHYSICAL_SILVER": AssetCategory.PHYSICAL_SILVER,
    "GOLD": AssetCategory.DIGITAL_GOLD,
    "SILVER": AssetCategory.DIGITAL_SILVER,
    "REAL_ESTATE": AssetCategory.REAL_ESTATE,
    "PROPERTY": AssetCategory.REAL_ESTATE,
    "CASH": AssetCategory.CASH,
    "SAVINGS": AssetCategory.CASH,
    "BANK": AssetCategory.CASH,
    "OTHER": AssetCategory.OTHER,
}


def normalize_asset_category(category_str: Optional[str]) -> AssetCategory:
    """Normalizes string or legacy alias into canonical AssetCategory enum."""
    if not category_str:
        return AssetCategory.OTHER
    cleaned = category_str.strip().upper()
    return CATEGORY_ALIASES.get(cleaned, AssetCategory.OTHER)
