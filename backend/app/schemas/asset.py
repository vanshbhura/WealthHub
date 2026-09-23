import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    platform_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    asset_type: str = Field(..., description="STOCKS, MUTUAL_FUNDS, DIGITAL_GOLD, P2P_LOANS, etc.")
    name: str = Field(..., min_length=1, max_length=255)
    symbol: Optional[str] = None
    identifier: Optional[str] = None
    quantity: float = Field(default=1.0, ge=0)
    average_buy_price: float = Field(default=0.0, ge=0)
    invested_amount: Optional[float] = None
    current_price: float = Field(default=0.0, ge=0)
    current_value: Optional[float] = None
    currency: str = "INR"
    purchase_date: Optional[date] = None
    data_source: str = "MANUAL"
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = Field(default=None, ge=0)
    average_buy_price: Optional[float] = Field(default=None, ge=0)
    invested_amount: Optional[float] = Field(default=None, ge=0)
    current_price: Optional[float] = Field(default=None, ge=0)
    current_value: Optional[float] = Field(default=None, ge=0)
    last_valued_at: Optional[datetime] = None
    metadata_json: Optional[Dict[str, Any]] = None


class AssetResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    account_id: Optional[uuid.UUID] = None
    platform_id: uuid.UUID
    asset_type: str
    name: str
    symbol: Optional[str] = None
    identifier: Optional[str] = None
    quantity: float
    average_buy_price: float
    invested_amount: float
    current_price: float
    current_value: float
    currency: str
    purchase_date: Optional[date] = None
    last_valued_at: Optional[datetime] = None
    data_source: str
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
