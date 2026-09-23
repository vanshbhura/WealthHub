import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.asset import Asset
from app.models.platform import Platform
from app.models.account import Account
from app.schemas.asset import AssetCreate, AssetUpdate, AssetResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/assets", tags=["Assets"])


@router.get("", response_model=List[AssetResponse])
def list_assets(
    asset_type: Optional[str] = Query(None, description="Filter by asset type: STOCKS, MUTUAL_FUNDS, DIGITAL_GOLD, P2P_LOANS, etc."),
    platform_id: Optional[uuid.UUID] = Query(None, description="Filter by platform UUID"),
    account_id: Optional[uuid.UUID] = Query(None, description="Filter by account UUID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve assets belonging to the authenticated user with optional filtering."""
    stmt = select(Asset).where(Asset.user_id == current_user.id)

    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type.upper().strip())
    if platform_id:
        stmt = stmt.where(Asset.platform_id == platform_id)
    if account_id:
        stmt = stmt.where(Asset.account_id == account_id)

    stmt = stmt.order_by(Asset.current_value.desc())
    assets = list(db.execute(stmt).scalars().all())
    return [AssetResponse.model_validate(a) for a in assets]


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new financial asset for the authenticated user."""
    # Verify platform exists
    plat = db.execute(select(Platform).where(Platform.id == payload.platform_id)).scalar_one_or_none()
    if not plat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PLATFORM_NOT_FOUND", "message": "Platform not found"}
        )

    # Verify account ownership if provided
    if payload.account_id:
        acc = db.execute(select(Account).where(Account.id == payload.account_id, Account.user_id == current_user.id)).scalar_one_or_none()
        if not acc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found or access denied"}
            )

    invested_amount = payload.invested_amount
    if invested_amount is None:
        invested_amount = round(payload.quantity * payload.average_buy_price, 2)

    current_value = payload.current_value
    if current_value is None:
        current_value = round(payload.quantity * payload.current_price, 2) if payload.current_price > 0 else invested_amount

    asset = Asset(
        user_id=current_user.id,
        account_id=payload.account_id,
        platform_id=payload.platform_id,
        asset_type=payload.asset_type.upper().strip(),
        name=payload.name.strip(),
        symbol=payload.symbol,
        identifier=payload.identifier,
        quantity=payload.quantity,
        average_buy_price=payload.average_buy_price,
        invested_amount=invested_amount,
        current_price=payload.current_price,
        current_value=current_value,
        currency=payload.currency.upper(),
        purchase_date=payload.purchase_date,
        last_valued_at=datetime.utcnow(),
        data_source=payload.data_source,
        metadata_json=payload.metadata_json or {},
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return AssetResponse.model_validate(asset)


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve asset details by ID ensuring user data isolation."""
    stmt = select(Asset).where(Asset.id == asset_id, Asset.user_id == current_user.id)
    asset = db.execute(stmt).scalar_one_or_none()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSET_NOT_FOUND", "message": "Asset not found"}
        )
    return AssetResponse.model_validate(asset)


@router.patch("/{asset_id}", response_model=AssetResponse)
def update_asset(
    asset_id: uuid.UUID,
    payload: AssetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update asset parameters (e.g. quantity, current valuation)."""
    stmt = select(Asset).where(Asset.id == asset_id, Asset.user_id == current_user.id)
    asset = db.execute(stmt).scalar_one_or_none()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSET_NOT_FOUND", "message": "Asset not found"}
        )

    if payload.name is not None:
        asset.name = payload.name.strip()
    if payload.quantity is not None:
        asset.quantity = payload.quantity
    if payload.average_buy_price is not None:
        asset.average_buy_price = payload.average_buy_price
    if payload.invested_amount is not None:
        asset.invested_amount = payload.invested_amount
    if payload.current_price is not None:
        asset.current_price = payload.current_price
    if payload.current_value is not None:
        asset.current_value = payload.current_value
    if payload.metadata_json is not None:
        asset.metadata_json = payload.metadata_json

    asset.last_valued_at = datetime.utcnow()
    db.commit()
    db.refresh(asset)
    return AssetResponse.model_validate(asset)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(
    asset_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an asset and its linked transactions."""
    stmt = select(Asset).where(Asset.id == asset_id, Asset.user_id == current_user.id)
    asset = db.execute(stmt).scalar_one_or_none()
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ASSET_NOT_FOUND", "message": "Asset not found"}
        )
    db.delete(asset)
    db.commit()
    return None
