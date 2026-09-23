import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TransactionCreate(BaseModel):
    asset_id: Optional[uuid.UUID] = None
    transaction_type: str = Field(..., description="BUY, SELL, DEPOSIT, WITHDRAWAL, DIVIDEND, INTEREST, FEE, TAX, REPAYMENT, OTHER")
    transaction_date: Optional[datetime] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: float
    fees: float = 0.0
    taxes: float = 0.0
    currency: str = "INR"
    external_transaction_id: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class TransactionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    asset_id: Optional[uuid.UUID] = None
    transaction_type: str
    transaction_date: datetime
    quantity: Optional[float] = None
    price: Optional[float] = None
    amount: float
    fees: float
    taxes: float
    currency: str
    external_transaction_id: Optional[str] = None
    metadata_json: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True
