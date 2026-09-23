import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.import_job import ImportJob
from app.models.connection import Connection, ConnectionType, ConnectionStatus
from app.models.platform import Platform
from app.models.asset import Asset
from app.connectors.dtos import (
    NormalizedPortfolio,
    NormalizedAccount,
    NormalizedAsset,
    NormalizedHolding,
    NormalizedTransaction,
)
from app.connectors.sync_service import SyncService
from app.services.portfolio_service import PortfolioService
from app.services.snapshot_service import SnapshotService
from app.imports.enums import ImportJobStatus, DuplicateStatus, ImportType
from app.imports.exceptions import CommitError, ValidationError


class CommitService:
    """
    Atomically commits validated statement rows into canonical WealthHub entities.
    Leverages SyncService's normalized portfolio pipeline for idempotent persistence,
    followed by portfolio recalculation and snapshot capture.
    """

    @classmethod
    def commit_import_job(
        cls,
        import_job_id: uuid.UUID,
        user_id: uuid.UUID,
        db: Session,
    ) -> Dict[str, Any]:
        # 1. Fetch import job with strict user isolation
        stmt = select(ImportJob).where(
            ImportJob.id == import_job_id, ImportJob.user_id == user_id
        )
        job = db.execute(stmt).scalar_one_or_none()
        if not job:
            raise CommitError("Import job not found or unauthorized.")

        if job.status == ImportJobStatus.COMMITTED.value:
            raise CommitError("This import job has already been committed.")

        if job.status == ImportJobStatus.CANCELLED.value:
            raise CommitError("This import job was cancelled.")

        if job.error_count > 0:
            raise ValidationError(
                f"Cannot commit statement with {job.error_count} unresolved errors. Please review and fix issues."
            )

        preview = job.preview_data or {}
        rows: List[Dict[str, Any]] = preview.get("rows", [])
        if not rows:
            raise CommitError("No parsed records available in this import job to commit.")

        # 2. Resolve or create platform connection
        plat_stmt = select(Platform).where(Platform.id == job.platform_id)
        platform = db.execute(plat_stmt).scalar_one_or_none()
        if not platform:
            raise CommitError("Associated platform does not exist.")

        conn_stmt = select(Connection).where(
            Connection.user_id == user_id,
            Connection.platform_id == job.platform_id,
        )
        connection = db.execute(conn_stmt).scalar_one_or_none()

        if not connection:
            connection = Connection(
                id=uuid.uuid4(),
                user_id=user_id,
                platform_id=job.platform_id,
                connection_type=ConnectionType.IMPORT.value,
                connector_key="statement_import",
                status=ConnectionStatus.CONNECTED.value,
            )
            db.add(connection)
            db.flush()
        else:
            # Update connection type if it was pending or manual
            if connection.connection_type != ConnectionType.IMPORT.value and connection.status != ConnectionStatus.CONNECTED.value:
                connection.connection_type = ConnectionType.IMPORT.value
            connection.status = ConnectionStatus.CONNECTED.value

        job.connection_id = connection.id

        # 3. Construct canonical NormalizedPortfolio from valid, non-duplicate rows
        accounts_map: Dict[str, NormalizedAccount] = {}
        assets_map: Dict[str, Dict[str, Any]] = {}
        norm_txs: List[NormalizedTransaction] = []

        skipped_duplicates = 0
        committed_transactions = 0

        for r in rows:
            if not r.get("is_valid", True):
                continue

            dup_status = r.get("duplicate_status")
            if dup_status == DuplicateStatus.EXACT_DUPLICATE.value:
                skipped_duplicates += 1
                continue

            # Account normalization
            acc_num = r.get("account_number") or f"{platform.name} Account"
            if acc_num not in accounts_map:
                accounts_map[acc_num] = NormalizedAccount(
                    account_name=acc_num if len(acc_num) > 4 else f"{platform.name} ({acc_num})",
                    account_type="SAVINGS" if job.import_type == ImportType.BANK.value else "DEMAT",
                    masked_identifier=f"****{acc_num[-4:]}" if len(acc_num) >= 4 else acc_num,
                    currency=r.get("currency", "INR"),
                    external_account_reference=acc_num,
                )

            # Asset normalization
            asset_name = r.get("asset_name") or r.get("symbol") or f"{platform.name} Asset"
            asset_ident = r.get("isin") or r.get("symbol") or asset_name
            asset_type = r.get("asset_type", "STOCKS")
            qty = r.get("quantity") or 0.0
            price = r.get("price") or 0.0
            amt = abs(r.get("amount") or 0.0)

            if asset_ident not in assets_map:
                assets_map[asset_ident] = {
                    "name": asset_name,
                    "asset_type": asset_type,
                    "symbol": r.get("symbol"),
                    "identifier": r.get("isin"),
                    "total_qty": 0.0,
                    "total_cost": 0.0,
                    "last_price": price,
                    "account_ref": acc_num,
                }

            # Accumulate holdings estimates from transactions
            tx_type = r.get("transaction_type", "BUY")
            if tx_type in ("BUY", "DEPOSIT", "TRANSFER_IN"):
                assets_map[asset_ident]["total_qty"] += float(qty)
                assets_map[asset_ident]["total_cost"] += float(amt)
            elif tx_type in ("SELL", "WITHDRAWAL", "TRANSFER_OUT"):
                assets_map[asset_ident]["total_qty"] = max(0.0, assets_map[asset_ident]["total_qty"] - float(qty))

            if price > 0:
                assets_map[asset_ident]["last_price"] = float(price)

            # Transaction DTO
            parsed_dt = datetime.strptime(r["date"], "%Y-%m-%d") if r.get("date") else datetime.utcnow()
            norm_tx = NormalizedTransaction(
                external_transaction_id=r.get("external_transaction_id"),
                transaction_type=tx_type,
                transaction_date=parsed_dt,
                quantity=float(qty) if qty else None,
                price=float(price) if price else None,
                amount=float(amt),
                currency=r.get("currency", "INR"),
                asset_identifier=asset_ident,
                metadata={
                    "fingerprint": r.get("fingerprint"),
                    "description": r.get("description"),
                    "source": "STATEMENT_IMPORT",
                    "import_job_id": str(job.id),
                },
            )
            norm_txs.append(norm_tx)
            committed_transactions += 1

        # Build NormalizedHolding objects
        norm_holdings: List[NormalizedHolding] = []
        for ident, a_info in assets_map.items():
            qty = a_info["total_qty"]
            last_price = a_info["last_price"]
            curr_val = qty * last_price if (qty > 0 and last_price > 0) else a_info["total_cost"]
            avg_price = (a_info["total_cost"] / qty) if qty > 0 else last_price

            norm_asset = NormalizedAsset(
                name=a_info["name"],
                asset_type=a_info["asset_type"],
                symbol=a_info["symbol"],
                identifier=a_info["identifier"],
                quantity=qty,
                average_buy_price=avg_price,
                invested_amount=a_info["total_cost"],
                current_price=last_price,
                current_value=curr_val,
                currency="INR",
            )
            norm_holdings.append(NormalizedHolding(
                asset=norm_asset,
                account_reference=a_info["account_ref"]
            ))

        # Assemble portfolio
        portfolio_dto = NormalizedPortfolio(
            accounts=list(accounts_map.values()),
            holdings=norm_holdings,
            transactions=norm_txs,
        )

        # 4. Atomic transaction persistence
        try:
            with db.begin_nested():
                stats = SyncService._apply_normalized_portfolio(
                    user_id=user_id,
                    platform_id=platform.id,
                    connection_id=connection.id,
                    portfolio=portfolio_dto,
                    db=db,
                )

            # 5. Recalculate portfolio and daily snapshot
            PortfolioService.get_summary(user_id=user_id, db=db)
            SnapshotService.capture_daily_snapshot(user_id=user_id, db=db)

            # 6. Finalize statuses
            now = datetime.utcnow()
            job.status = ImportJobStatus.COMMITTED.value
            job.committed_at = now
            job.updated_at = now
            job.new_count = committed_transactions
            job.duplicate_count = skipped_duplicates

            connection.status = ConnectionStatus.CONNECTED.value
            connection.last_synced_at = now
            connection.last_sync_status = "SUCCESS"
            connection.last_sync_error = None

            db.commit()

            return {
                "import_job_id": str(job.id),
                "platform_id": str(platform.id),
                "platform_name": platform.name,
                "status": "COMMITTED",
                "committed_transactions": committed_transactions,
                "skipped_duplicates": skipped_duplicates,
                "assets_processed": len(norm_holdings),
                "records_created": stats["created"],
                "records_updated": stats["updated"],
                "committed_at": now.isoformat(),
            }

        except Exception as e:
            db.rollback()
            job.status = ImportJobStatus.FAILED.value
            job.error_message = f"Failed to commit statement: {str(e)}"
            db.commit()
            raise CommitError(f"Statement commit transaction failed: {str(e)}")
