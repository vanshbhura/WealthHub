import uuid
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PortfolioSummaryResponse(BaseModel):
    total_wealth: float
    invested_value: float
    profit_loss: float
    profit_loss_percentage: Optional[float] = None
    today_change: Optional[float] = None
    today_change_percentage: Optional[float] = None
    cash_value: float
    currency: str = "INR"
    asset_count: int = 0
    platform_count: int = 0
    last_updated: datetime
    data_freshness: str = "UNKNOWN"
    data_quality: Dict[str, Any] = Field(default_factory=dict)


class PortfolioPlatformItem(BaseModel):
    platform_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    platform_name: str
    platform_slug: str
    category: str
    integration_type: str
    status: str
    current_value: float
    invested_value: float
    profit_loss: float
    profit_loss_percentage: Optional[float] = None
    today_change: Optional[float] = None
    today_change_percentage: Optional[float] = None
    last_updated: Optional[datetime] = None
    logo_url: Optional[str] = None
    asset_count: int = 0
    holdings_count: int = 0
    freshness_status: str = "UNKNOWN"


class AssetCalculatedResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    platform_id: uuid.UUID
    platform_name: str
    account_id: Optional[uuid.UUID] = None
    name: str
    symbol: Optional[str] = None
    asset_type: str
    quantity: float
    average_buy_price: float
    invested_value: float
    current_price: float
    current_value: float
    profit_loss: float
    profit_loss_percentage: Optional[float] = None
    last_valued_at: Optional[datetime] = None
    data_source: str
    freshness_status: str
    currency: str = "INR"
    p2p_details: Optional[Dict[str, Any]] = None
    precious_metal_details: Optional[Dict[str, Any]] = None


class SnapshotItemResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    date: str
    snapshot_date: date
    value: float
    total_value: float
    invested_value: float
    profit_loss: float
    profit_loss_percentage: Optional[float] = None
    cash_value: float
    asset_allocation: Dict[str, Any] = Field(default_factory=dict)
    platform_values: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


PortfolioSnapshotResponse = SnapshotItemResponse


class HistoricalSnapshotsResponse(BaseModel):
    period: str
    has_sufficient_history: bool
    data_points_count: int
    snapshots: List[SnapshotItemResponse]


class AllocationSliceSchema(BaseModel):
    key: str
    label: str
    value: float
    percentage: float


class PortfolioAllocationResponse(BaseModel):
    total_basis: float
    by_asset_type: List[AllocationSliceSchema]
    by_platform: List[AllocationSliceSchema]
