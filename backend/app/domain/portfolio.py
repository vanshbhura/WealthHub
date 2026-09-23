import uuid
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from app.domain.enums import AssetCategory, DataFreshnessStatus, DataSource


@dataclass
class AllocationSliceDomain:
    key: str
    label: str
    value: float
    percentage: float


@dataclass
class PlatformTotalDomain:
    platform_id: uuid.UUID
    platform_name: str
    platform_slug: str
    category: str
    integration_type: str
    status: str
    invested_value: float
    current_value: float
    profit_loss: float
    profit_loss_percentage: Optional[float]
    today_change: Optional[float]
    today_change_percentage: Optional[float]
    asset_count: int
    last_updated: Optional[datetime]
    logo_url: Optional[str] = None
    freshness_status: DataFreshnessStatus = DataFreshnessStatus.UNKNOWN


@dataclass
class AssetCalculatedDomain:
    id: uuid.UUID
    user_id: uuid.UUID
    platform_id: uuid.UUID
    platform_name: str
    account_id: Optional[uuid.UUID]
    name: str
    symbol: Optional[str]
    asset_type: str
    canonical_category: AssetCategory
    quantity: float
    average_buy_price: float
    invested_value: float
    current_price: float
    current_value: float
    profit_loss: float
    profit_loss_percentage: Optional[float]
    currency: str
    data_source: str
    freshness_status: DataFreshnessStatus
    last_valued_at: Optional[datetime]
    metadata: Dict[str, Any] = field(default_factory=dict)
    p2p_details: Optional[Dict[str, Any]] = None
    precious_metal_details: Optional[Dict[str, Any]] = None


@dataclass
class PortfolioSummaryDomain:
    total_wealth: float
    invested_value: float
    profit_loss: float
    profit_loss_percentage: Optional[float]
    today_change: Optional[float]
    today_change_percentage: Optional[float]
    cash_value: float
    currency: str
    asset_count: int
    platform_count: int
    last_updated: datetime
    data_freshness: DataFreshnessStatus
    data_quality: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapshotDomain:
    id: uuid.UUID
    user_id: uuid.UUID
    snapshot_date: date
    total_value: float
    invested_value: float
    profit_loss: float
    profit_loss_percentage: Optional[float]
    cash_value: float
    asset_allocation: Dict[str, float]
    platform_values: Dict[str, float]
    created_at: datetime
