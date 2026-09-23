import uuid
from typing import List, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.transaction import Transaction
from app.imports.enums import DuplicateStatus
from app.imports.fingerprints import generate_transaction_fingerprint


class DeduplicationService:
    """
    Identifies exact and possible duplicates between incoming statement rows
    and existing database transactions or earlier rows within the statement.
    """

    @staticmethod
    def evaluate_duplicates(
        user_id: uuid.UUID,
        platform_id: uuid.UUID,
        normalized_rows: List[Dict[str, Any]],
        db: Session,
    ) -> List[Dict[str, Any]]:
        """
        Tags each normalized row with duplicate_status ('NEW', 'EXACT_DUPLICATE', 'POSSIBLE_DUPLICATE')
        and assigns computed fingerprint and external_transaction_id.
        """
        # Fetch existing transactions for user
        tx_stmt = select(Transaction).where(Transaction.user_id == user_id)
        existing_txs = list(db.execute(tx_stmt).scalars().all())

        existing_ext_ids: Set[str] = set()
        existing_fingerprints: Set[str] = set()
        existing_signatures: Set[str] = set()  # date|amount|asset

        for tx in existing_txs:
            if tx.external_transaction_id:
                existing_ext_ids.add(tx.external_transaction_id)
            if tx.metadata_json and isinstance(tx.metadata_json, dict):
                fp = tx.metadata_json.get("fingerprint")
                if fp:
                    existing_fingerprints.add(fp)

            date_str = tx.transaction_date.strftime("%Y-%m-%d") if tx.transaction_date else ""
            sig = f"{date_str}|{round(float(tx.amount), 2)}"
            existing_signatures.add(sig)

        seen_batch_ids: Set[str] = set()
        seen_batch_fps: Set[str] = set()

        processed_rows: List[Dict[str, Any]] = []

        for row in normalized_rows:
            tx_id = row.get("transaction_id")
            row_date = row.get("date")
            row_type = row.get("transaction_type")
            row_amount = row.get("amount")
            asset_ident = row.get("symbol") or row.get("isin") or row.get("asset_name")
            row_qty = row.get("quantity")
            row_price = row.get("price")
            row_desc = row.get("description")

            # Compute canonical fingerprint
            fp = generate_transaction_fingerprint(
                user_id=user_id,
                platform_id=platform_id,
                transaction_date=row_date,
                transaction_type=row_type,
                amount=row_amount,
                asset_identifier=asset_ident,
                quantity=row_qty,
                price=row_price,
                reference_id=tx_id or row_desc,
            )
            row["fingerprint"] = fp

            # If no provider tx_id was found in the statement, use fingerprint as external ID
            canonical_ext_id = tx_id if tx_id else f"fp_{fp[:16]}"
            row["external_transaction_id"] = canonical_ext_id

            # Duplicate Evaluation
            if tx_id and (tx_id in existing_ext_ids or tx_id in seen_batch_ids):
                row["duplicate_status"] = DuplicateStatus.EXACT_DUPLICATE.value
                row["duplicate_reason"] = f"Transaction ID '{tx_id}' already exists in database or file."
            elif fp in existing_fingerprints or fp in seen_batch_fps:
                row["duplicate_status"] = DuplicateStatus.EXACT_DUPLICATE.value
                row["duplicate_reason"] = "Identical transaction fingerprint already exists."
            else:
                # Check possible duplicate: same date and same amount
                date_str = str(row_date or "")[:10]
                sig = f"{date_str}|{round(float(row_amount or 0.0), 2)}"
                if sig in existing_signatures:
                    row["duplicate_status"] = DuplicateStatus.POSSIBLE_DUPLICATE.value
                    row["duplicate_reason"] = "Existing transaction matches same date and amount."
                else:
                    row["duplicate_status"] = DuplicateStatus.NEW.value
                    row["duplicate_reason"] = None

            if tx_id:
                seen_batch_ids.add(tx_id)
            seen_batch_fps.add(fp)

            processed_rows.append(row)

        return processed_rows
