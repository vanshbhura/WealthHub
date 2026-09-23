import uuid
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.platform import Platform
from app.schemas.portfolio import (
    PortfolioSummaryResponse,
    PortfolioPlatformItem,
    AssetCalculatedResponse,
    SnapshotItemResponse,
    HistoricalSnapshotsResponse,
    PortfolioAllocationResponse,
)
from app.dependencies import get_current_user
from app.services.portfolio_service import PortfolioService
from app.services.snapshot_service import SnapshotService

router = APIRouter(prefix="/api/portfolio", tags=["Portfolio"])


@router.get("/summary", response_model=PortfolioSummaryResponse)
def get_portfolio_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get live consolidated portfolio summary for the user calculated across database records:
    Total wealth, invested value, P&L, P&L %, daily movement, freshness, and quality indicators.
    """
    summary = PortfolioService.get_summary(user_id=current_user.id, db=db)
    return PortfolioSummaryResponse(**summary)


@router.get("/platforms", response_model=List[PortfolioPlatformItem])
def get_connected_platforms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get aggregated platform breakdown for connected investment cards.
    """
    breakdown = PortfolioService.get_platform_breakdown(user_id=current_user.id, db=db)
    return [PortfolioPlatformItem(**item) for item in breakdown]


@router.get("/assets", response_model=List[AssetCalculatedResponse])
def get_calculated_assets(
    platform: Optional[str] = Query(None, description="Platform slug or UUID"),
    asset_type: Optional[str] = Query(None, description="Normalized asset type"),
    account: Optional[uuid.UUID] = Query(None, description="Account UUID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get normalized calculated asset data with filters for platform, asset category, or account.
    """
    platform_id = None
    if platform:
        try:
            platform_id = uuid.UUID(platform)
        except ValueError:
            # Match platform slug
            from sqlalchemy import select
            plat_rec = db.execute(select(Platform).where(Platform.slug == platform.lower().strip())).scalar_one_or_none()
            if plat_rec:
                platform_id = plat_rec.id

    assets = PortfolioService.get_assets_calculated(
        user_id=current_user.id,
        db=db,
        platform_id=platform_id,
        asset_type=asset_type,
        account_id=account
    )
    return [AssetCalculatedResponse(**a) for a in assets]


@router.get("/snapshots", response_model=Union[HistoricalSnapshotsResponse, List[SnapshotItemResponse]])
def get_portfolio_snapshots(
    period: Optional[str] = Query(None, pattern="^(1M|2M|6M|12M|24M|5Y)$", description="Period filter (1M, 2M, 6M, 12M, 24M, 5Y)"),
    timeframe: Optional[str] = Query(None, pattern="^(1M|2M|6M|12M|24M|5Y)$", description="Backwards-compatible timeframe alias"),
    envelope: bool = Query(False, description="Whether to return full metadata envelope"),
    response: Response = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve chronological historical portfolio snapshots.
    Never fabricates fake points. When history is insufficient, exposes status flag.
    """
    active_period = period or timeframe or "1M"
    data = SnapshotService.get_snapshots(user_id=current_user.id, period=active_period, db=db)

    if response is not None:
        response.headers["X-Has-Sufficient-History"] = str(data["has_sufficient_history"]).lower()
        response.headers["X-Data-Points-Count"] = str(data["data_points_count"])

    if envelope:
        return HistoricalSnapshotsResponse(**data)

    return [SnapshotItemResponse(**s) for s in data["snapshots"]]


@router.get("/allocation", response_model=PortfolioAllocationResponse)
def get_portfolio_allocation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve portfolio allocation by asset type and platform.
    Percentages sum strictly to 100.0%.
    """
    allocation = PortfolioService.get_portfolio_allocation(user_id=current_user.id, db=db)
    return PortfolioAllocationResponse(**allocation)


@router.post("/snapshots/capture", response_model=SnapshotItemResponse)
def capture_daily_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger immediate idempotent portfolio snapshot capture for the current user.
    """
    snapshot = SnapshotService.capture_daily_snapshot(user_id=current_user.id, db=db)
    return SnapshotItemResponse(
        id=snapshot.id,
        date=snapshot.snapshot_date.isoformat(),
        snapshot_date=snapshot.snapshot_date,
        value=snapshot.total_value,
        total_value=snapshot.total_value,
        invested_value=snapshot.invested_value,
        profit_loss=snapshot.profit_loss,
        profit_loss_percentage=snapshot.profit_loss_percentage,
        cash_value=snapshot.cash_value,
        asset_allocation=snapshot.asset_allocation or {},
        platform_values=snapshot.platform_values or {},
        created_at=snapshot.created_at
    )
