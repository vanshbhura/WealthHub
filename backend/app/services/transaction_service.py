import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.transaction import Transaction
from app.models.asset import Asset
from app.schemas.transaction import TransactionCreate


class TransactionService:
    @staticmethod
    def create_transaction(user_id: uuid.UUID, data: TransactionCreate, db: Session) -> Transaction:
        """Create a new transaction and update associated asset if relevant."""
        asset = None
        if data.asset_id:
            asset_stmt = select(Asset).where(Asset.id == data.asset_id, Asset.user_id == user_id)
            asset = db.execute(asset_stmt).scalar_one_or_none()
            if not asset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={"code": "ASSET_NOT_FOUND", "message": "Asset does not exist or does not belong to user"}
                )

        tx = Transaction(
            user_id=user_id,
            asset_id=data.asset_id,
            transaction_type=data.transaction_type.upper(),
            transaction_date=data.transaction_date or datetime.utcnow(),
            quantity=data.quantity,
            price=data.price,
            amount=data.amount,
            fees=data.fees,
            taxes=data.taxes,
            currency=data.currency,
            external_transaction_id=data.external_transaction_id,
            metadata_json=data.metadata_json or {}
        )
        db.add(tx)

        # Update asset quantity/invested_amount for BUY/SELL
        if asset and data.quantity is not None:
            if tx.transaction_type == "BUY":
                new_qty = asset.quantity + data.quantity
                new_invested = asset.invested_amount + data.amount + data.fees + data.taxes
                asset.quantity = new_qty
                asset.invested_amount = new_invested
                if new_qty > 0:
                    asset.average_buy_price = round(new_invested / new_qty, 2)
                if asset.current_price > 0:
                    asset.current_value = round(new_qty * asset.current_price, 2)
            elif tx.transaction_type == "SELL":
                new_qty = max(0.0, asset.quantity - data.quantity)
                # Reduce invested proportionately
                if asset.quantity > 0:
                    proportion_sold = min(1.0, data.quantity / asset.quantity)
                    asset.invested_amount = round(asset.invested_amount * (1 - proportion_sold), 2)
                asset.quantity = new_qty
                if asset.current_price > 0:
                    asset.current_value = round(new_qty * asset.current_price, 2)

        db.commit()
        db.refresh(tx)
        return tx
