import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.asset import Asset
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.dependencies import get_current_user
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/api/transactions", tags=["Transactions"])


@router.get("", response_model=List[TransactionResponse])
def list_transactions(
    asset_id: Optional[uuid.UUID] = Query(None, description="Filter by asset UUID"),
    platform_id: Optional[uuid.UUID] = Query(None, description="Filter by platform UUID"),
    transaction_type: Optional[str] = Query(None, description="Filter by BUY, SELL, DIVIDEND, INTEREST, etc."),
    from_date: Optional[datetime] = Query(None, description="Start date filter"),
    to_date: Optional[datetime] = Query(None, description="End date filter"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List transactions for the authenticated user with optional asset, platform, and type filtering."""
    stmt = select(Transaction).where(Transaction.user_id == current_user.id)

    if platform_id:
        stmt = stmt.join(Asset, Transaction.asset_id == Asset.id).where(Asset.platform_id == platform_id)
    if asset_id:
        stmt = stmt.where(Transaction.asset_id == asset_id)
    if transaction_type:
        stmt = stmt.where(Transaction.transaction_type == transaction_type.upper().strip())
    if from_date:
        stmt = stmt.where(Transaction.transaction_date >= from_date)
    if to_date:
        stmt = stmt.where(Transaction.transaction_date <= to_date)

    stmt = stmt.order_by(Transaction.transaction_date.desc()).limit(limit).offset(offset)
    txs = list(db.execute(stmt).scalars().all())
    return [TransactionResponse.model_validate(t) for t in txs]


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a financial transaction and dynamically adjust asset positions."""
    tx = TransactionService.create_transaction(user_id=current_user.id, data=payload, db=db)
    return TransactionResponse.model_validate(tx)


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve transaction by ID ensuring user data isolation."""
    stmt = select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == current_user.id)
    tx = db.execute(stmt).scalar_one_or_none()
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "TRANSACTION_NOT_FOUND", "message": "Transaction not found"}
        )
    return TransactionResponse.model_validate(tx)
