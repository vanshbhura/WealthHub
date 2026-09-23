import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class NormalizedAccount(BaseModel):
    """Normalized account representation (e.g. Demat, Savings, Crypto Wallet, P2P Account)."""
    account_name: str
    account_type: str = "DEMAT"  # DEMAT, SAVINGS, P2P_WALLET, CRYPTO_WALLET, etc.
    masked_identifier: Optional[str] = None
    currency: str = "INR"
    current_value: float = 0.0
    invested_value: float = 0.0
    external_account_reference: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedAsset(BaseModel):
    """Normalized asset representation (e.g. Stock, Mutual Fund, FD, Gold, Crypto)."""
    name: str
    asset_type: str  # STOCKS, MUTUAL_FUNDS, FIXED_DEPOSITS, DIGITAL_GOLD, etc.
    symbol: Optional[str] = None
    identifier: Optional[str] = None  # ISIN / Folio / Contract / Token address
    quantity: float = 0.0
    average_buy_price: float = 0.0
    invested_amount: float = 0.0
    current_price: float = 0.0
    current_value: float = 0.0
    currency: str = "INR"
    purchase_date: Optional[date] = None
    last_valued_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedHolding(BaseModel):
    """Wrapper holding combining an asset with optional account affiliation."""
    asset: NormalizedAsset
    account_reference: Optional[str] = None


class NormalizedTransaction(BaseModel):
    """Normalized transaction (e.g. BUY, SELL, DIVIDEND, INTEREST, REPAYMENT)."""
    external_transaction_id: Optional[str] = None
    transaction_type: str = "BUY"  # BUY, SELL, DEPOSIT, WITHDRAWAL, DIVIDEND, INTEREST, etc.
    transaction_date: datetime = Field(default_factory=datetime.utcnow)
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: float
    fees: float = 0.0
    taxes: float = 0.0
    currency: str = "INR"
    asset_identifier: Optional[str] = None  # ISIN or symbol matching the asset
    transfer_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NormalizedBalance(BaseModel):
    """Normalized cash/margin balances for a platform."""
    currency: str = "INR"
    available_cash: float = 0.0
    invested_amount: float = 0.0
    total_balance: float = 0.0
    as_of: datetime = Field(default_factory=datetime.utcnow)


class NormalizedPortfolio(BaseModel):
    """Aggregated normalized output from a connector sync execution."""
    accounts: List[NormalizedAccount] = Field(default_factory=list)
    holdings: List[NormalizedHolding] = Field(default_factory=list)
    transactions: List[NormalizedTransaction] = Field(default_factory=list)
    balances: List[NormalizedBalance] = Field(default_factory=list)


class SyncResult(BaseModel):
    """Summary of a completed sync execution."""
    status: str  # SUCCESS, SYNC_FAILED, SKIPPED
    records_processed: int = 0
    records_created: int = 0
    records_updated: int = 0
    error_code: Optional[str] = None
    safe_error_message: Optional[str] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)
