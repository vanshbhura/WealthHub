import uuid
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class SetuConsentRequest(BaseModel):
    """Request payload to initiate a Setu AA sandbox consent session."""
    customer_phone: Optional[str] = None
    customer_vpa: Optional[str] = None
    fi_types: List[str] = Field(
        default_factory=lambda: ["DEPOSIT", "TERM_DEPOSIT", "MUTUAL_FUNDS", "EQUITIES", "NPS"]
    )
    fetch_type: str = "PERIODIC"  # ONETIME or PERIODIC
    consent_mode: str = "STORE"   # VIEW or STORE
    expiry_days: int = 90
    redirect_url: Optional[str] = None


class SetuConsentResponse(BaseModel):
    """Response returned upon creating a consent request in Setu sandbox."""
    id: str  # Setu consent ID (e.g., uuid string)
    url: Optional[str] = None  # Web/mobile authorization redirect URL
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SetuConsentStatus(BaseModel):
    """Current status of a Setu AA consent request."""
    id: str
    status: str  # PENDING, ACTIVE, REJECTED, REVOKED, EXPIRED, ERROR
    handle: Optional[str] = None
    fi_types: List[str] = Field(default_factory=list)
    data_range_from: Optional[datetime] = None
    data_range_to: Optional[datetime] = None
    consent_expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SetuDataSessionRequest(BaseModel):
    """Request to initiate a data fetch session for an ACTIVE consent."""
    consent_id: str
    format: str = "json"


class SetuDataSessionResponse(BaseModel):
    """Response from initiating a data session."""
    id: str  # Session ID
    status: str = "PENDING"  # PENDING, COMPLETED, FAILED


class SetuBankTransaction(BaseModel):
    """Bank account transaction record."""
    txn_id: str
    type: str  # CREDIT, DEBIT
    amount: float
    narration: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    balance_after: Optional[float] = None


class SetuBankAccount(BaseModel):
    """Bank deposit account details."""
    fip_id: str
    bank_name: str
    account_number_masked: str
    account_type: str = "SAVINGS"  # SAVINGS, CURRENT
    current_balance: float = 0.0
    currency: str = "INR"
    transactions: List[SetuBankTransaction] = Field(default_factory=list)


class SetuMutualFundHolding(BaseModel):
    """Mutual Fund holding record from CAS/CAMS/KFintech."""
    amc: str
    scheme_name: str
    isin: str
    folio_number: str
    units: float
    nav: float
    nav_date: Optional[date] = None
    invested_value: float = 0.0
    current_value: float = 0.0


class SetuEquityHolding(BaseModel):
    """Depository equity holding (CDSL / NSDL)."""
    isin: str
    company_name: str
    symbol: Optional[str] = None
    demat_account: str
    depository: str = "CDSL"
    quantity: float
    average_buy_price: float = 0.0
    current_price: float = 0.0
    current_value: float = 0.0


class SetuFixedDeposit(BaseModel):
    """Term / Fixed Deposit record."""
    bank_name: str
    deposit_number_masked: str
    principal_amount: float
    current_value: float
    interest_rate: float = 0.0
    maturity_date: Optional[date] = None
    tenure_months: Optional[int] = None


class SetuNPSAccount(BaseModel):
    """National Pension System (NPS) PRAN holding."""
    pran_masked: str
    tier: str = "TIER_1"
    total_contribution: float = 0.0
    current_value: float = 0.0


class SetuFinancialDataResponse(BaseModel):
    """Aggregated financial information payload returned by Setu data session."""
    consent_id: str
    data_source: str = "SANDBOX_MOCK"
    bank_accounts: List[SetuBankAccount] = Field(default_factory=list)
    mutual_funds: List[SetuMutualFundHolding] = Field(default_factory=list)
    equities: List[SetuEquityHolding] = Field(default_factory=list)
    fixed_deposits: List[SetuFixedDeposit] = Field(default_factory=list)
    nps_accounts: List[SetuNPSAccount] = Field(default_factory=list)
