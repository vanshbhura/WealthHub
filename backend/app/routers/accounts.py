import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.account import Account
from app.models.platform import Platform
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.get("", response_model=List[AccountResponse])
def list_accounts(
    platform_id: Optional[uuid.UUID] = Query(None, description="Filter by platform ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List financial accounts belonging exclusively to the authenticated user."""
    stmt = select(Account).where(Account.user_id == current_user.id)
    if platform_id:
        stmt = stmt.where(Account.platform_id == platform_id)
    stmt = stmt.order_by(Account.current_value.desc())
    accounts = list(db.execute(stmt).scalars().all())
    return [AccountResponse.model_validate(a) for a in accounts]


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new financial account for the user."""
    plat = db.execute(select(Platform).where(Platform.id == payload.platform_id)).scalar_one_or_none()
    if not plat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PLATFORM_NOT_FOUND", "message": "Specified platform does not exist"}
        )

    account = Account(
        user_id=current_user.id,
        connection_id=payload.connection_id,
        platform_id=payload.platform_id,
        account_name=payload.account_name.strip(),
        account_type=payload.account_type.upper().strip(),
        masked_identifier=payload.masked_identifier,
        currency=payload.currency.upper(),
        current_value=payload.current_value,
        invested_value=payload.invested_value,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return AccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=AccountResponse)
def get_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve an account by ID ensuring user ownership."""
    stmt = select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    account = db.execute(stmt).scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found"}
        )
    return AccountResponse.model_validate(account)


@router.patch("/{account_id}", response_model=AccountResponse)
def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update account details or balances."""
    stmt = select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    account = db.execute(stmt).scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found"}
        )

    if payload.account_name is not None:
        account.account_name = payload.account_name.strip()
    if payload.current_value is not None:
        account.current_value = payload.current_value
    if payload.invested_value is not None:
        account.invested_value = payload.invested_value
    if payload.masked_identifier is not None:
        account.masked_identifier = payload.masked_identifier

    db.commit()
    db.refresh(account)
    return AccountResponse.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an account."""
    stmt = select(Account).where(Account.id == account_id, Account.user_id == current_user.id)
    account = db.execute(stmt).scalar_one_or_none()
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ACCOUNT_NOT_FOUND", "message": "Account not found"}
        )
    db.delete(account)
    db.commit()
    return None
