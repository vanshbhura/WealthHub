import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AccountCreate(BaseModel):
    platform_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    account_name: str = Field(..., min_length=2, max_length=150)
    account_type: str = Field(..., description="DEMAT, SAVINGS, P2P_WALLET, GOLD_LOCKER, etc.")
    masked_identifier: Optional[str] = None
    currency: str = "INR"
    current_value: float = 0.0
    invested_value: float = 0.0


class AccountUpdate(BaseModel):
    account_name: Optional[str] = Field(None, min_length=2, max_length=150)
    current_value: Optional[float] = None
    invested_value: Optional[float] = None
    masked_identifier: Optional[str] = None


class AccountResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    platform_id: uuid.UUID
    account_name: str
    account_type: str
    masked_identifier: Optional[str] = None
    currency: str
    current_value: float
    invested_value: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
