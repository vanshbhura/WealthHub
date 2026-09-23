import uuid
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.connection import Connection
from app.models.platform import Platform
from app.models.account import Account
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.models.sync_log import SyncLog, SyncStatus
from app.connectors.registry import registry
from app.connectors.exceptions import (
    ConnectorError,
    ConnectorNotImplementedError,
    SyncFailedError,
)
from app.connectors.dtos import SyncResult, NormalizedPortfolio
from app.services.portfolio_service import PortfolioService
from app.services.snapshot_service import SnapshotService


class SyncService:
    """
    Generic, idempotent synchronization engine for WealthHub connections.
    Coordinates connector execution, transactional upserts, portfolio recalculation,
    and granular sync history logging.
    """

    @staticmethod
    async def sync_connection(
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
        db: Session,
        connector_override=None
    ) -> SyncResult:
        """
        Executes an idempotent sync for the given connection.
        Ensures user isolation and records safe sync logs.
        """
        # 1. Load connection scoped to user
        conn_stmt = select(Connection).where(
            Connection.id == connection_id, Connection.user_id == user_id
        )
        connection = db.execute(conn_stmt).scalar_one_or_none()
        if not connection:
            raise SyncFailedError("Connection not found or unauthorized.")

        # Load platform
        plat_stmt = select(Platform).where(Platform.id == connection.platform_id)
        platform = db.execute(plat_stmt).scalar_one_or_none()
        if not platform:
            raise SyncFailedError("Associated platform does not exist.")

        # 2. Create started SyncLog
        sync_log = SyncLog(
            connection_id=connection.id,
            started_at=datetime.utcnow(),
            status=SyncStatus.STARTED.value,
        )
        db.add(sync_log)
        connection.status = "SYNCING"
        connection.last_sync_status = "SYNCING"
        db.commit()
        db.refresh(sync_log)

        # 3. Resolve connector
        connector_key = connection.connector_key or (
            "manual_asset" if connection.connection_type == "MANUAL" else platform.slug
        )

        connector = connector_override or registry.get(connector_key)
        if not connector:
            # Check if platform has any connector
            plat_connectors = registry.get_for_platform(platform.slug)
            connector = plat_connectors[0] if plat_connectors else None

        if not connector:
            err = ConnectorNotImplementedError(
                f"No connector registered for platform '{platform.name}'."
            )
            return SyncService._handle_sync_failure(
                connection, sync_log, err, db
            )

        # 4. Check availability
        if not connector.is_available():
            err = ConnectorNotImplementedError(
                f"{connector.name} is coming soon and cannot be synchronized yet."
            )
            return SyncService._handle_sync_failure(
                connection, sync_log, err, db
            )

        # 5. Execute connector sync
        try:
            normalized_portfolio: NormalizedPortfolio = await connector.sync(connection)

            # Double-counting protection: detect & flag cross-platform overlapping holdings
            from app.services.deduplication_engine import DeduplicationEngine
            DeduplicationEngine.flag_overlapping_holdings(
                user_id=user_id,
                platform_id=platform.id,
                portfolio=normalized_portfolio,
                db=db,
            )
            # Deduplicate transactions against existing records
            normalized_portfolio.transactions = DeduplicationEngine.deduplicate_transactions(
                user_id=user_id,
                transactions=normalized_portfolio.transactions,
                db=db,
            )

            # 6. Idempotent database upsert inside savepoint
            with db.begin_nested():
                stats = SyncService._apply_normalized_portfolio(
                    user_id=user_id,
                    platform_id=platform.id,
                    connection_id=connection.id,
                    portfolio=normalized_portfolio,
                    db=db,
                )

            # 7. Recalculate portfolio and capture snapshot
            PortfolioService.get_summary(user_id=user_id, db=db)
            SnapshotService.capture_daily_snapshot(user_id=user_id, db=db)

            # 8. Record success
            now = datetime.utcnow()
            connection.status = "SYNCED" if connection.connection_type != "MANUAL" else "CONNECTED"
            connection.last_synced_at = now
            connection.last_sync_status = "SUCCESS"
            connection.last_sync_error = None
            connection.last_data_fetch = now
            if getattr(connection, "consent_id", None):
                connection.last_consent_sync = now

            sync_log.status = SyncStatus.SUCCESS.value
            sync_log.completed_at = now
            sync_log.records_processed = stats["processed"]
            sync_log.records_created = stats["created"]
            sync_log.records_updated = stats["updated"]

            db.commit()

            return SyncResult(
                status="SUCCESS",
                records_processed=stats["processed"],
                records_created=stats["created"],
                records_updated=stats["updated"],
                completed_at=now,
            )

        except ConnectorError as ce:
            return SyncService._handle_sync_failure(connection, sync_log, ce, db)
        except Exception as ex:
            safe_err = SyncFailedError(f"Sync failed due to an unexpected error: {ex}")
            return SyncService._handle_sync_failure(connection, sync_log, safe_err, db)

    @staticmethod
    def _apply_normalized_portfolio(
        user_id: uuid.UUID,
        platform_id: uuid.UUID,
        connection_id: uuid.UUID,
        portfolio: NormalizedPortfolio,
        db: Session,
    ) -> Dict[str, int]:
        """
        Applies normalized accounts, holdings, and transactions idempotently.
        Ensures running sync twice produces zero duplicate records.
        """
        created = 0
        updated = 0
        processed = 0

        # --- A. UPSERT ACCOUNTS ---
        account_ref_to_id: Dict[str, uuid.UUID] = {}

        for norm_acc in portfolio.accounts:
            processed += 1
            # Match existing account
            match_stmt = select(Account).where(
                Account.user_id == user_id,
                Account.platform_id == platform_id,
            )
            if norm_acc.masked_identifier:
                match_stmt = match_stmt.where(
                    Account.masked_identifier == norm_acc.masked_identifier
                )
            else:
                match_stmt = match_stmt.where(
                    Account.account_name == norm_acc.account_name
                )

            acc = db.execute(match_stmt).scalar_one_or_none()

            if acc:
                # Update existing
                acc.current_value = norm_acc.current_value
                acc.invested_value = norm_acc.invested_value
                acc.connection_id = connection_id
                acc.updated_at = datetime.utcnow()
                updated += 1
            else:
                # Create new
                acc = Account(
                    user_id=user_id,
                    connection_id=connection_id,
                    platform_id=platform_id,
                    account_name=norm_acc.account_name,
                    account_type=norm_acc.account_type,
                    masked_identifier=norm_acc.masked_identifier,
                    currency=norm_acc.currency,
                    current_value=norm_acc.current_value,
                    invested_value=norm_acc.invested_value,
                )
                db.add(acc)
                db.flush()
                created += 1

            if norm_acc.external_account_reference:
                account_ref_to_id[norm_acc.external_account_reference] = acc.id

        # --- B. UPSERT HOLDINGS & ASSETS ---
        for holding in portfolio.holdings:
            processed += 1
            asset_dto = holding.asset
            acc_id = account_ref_to_id.get(holding.account_reference) if holding.account_reference else None

            # Match existing asset idempotently
            match_asset_stmt = select(Asset).where(
                Asset.user_id == user_id,
                Asset.platform_id == platform_id,
            )

            if asset_dto.identifier:
                match_asset_stmt = match_asset_stmt.where(
                    Asset.identifier == asset_dto.identifier
                )
            elif asset_dto.symbol:
                match_asset_stmt = match_asset_stmt.where(
                    Asset.symbol == asset_dto.symbol,
                    Asset.asset_type == asset_dto.asset_type,
                )
            else:
                match_asset_stmt = match_asset_stmt.where(
                    Asset.name == asset_dto.name,
                    Asset.asset_type == asset_dto.asset_type,
                )

            asset_entity = db.execute(match_asset_stmt).scalar_one_or_none()

            if asset_entity:
                # Update holding valuation
                asset_entity.quantity = asset_dto.quantity
                asset_entity.average_buy_price = asset_dto.average_buy_price
                asset_entity.invested_amount = asset_dto.invested_amount
                asset_entity.current_price = asset_dto.current_price
                asset_entity.current_value = asset_dto.current_value
                asset_entity.last_valued_at = datetime.utcnow()
                asset_entity.data_source = asset_dto.metadata.get("data_source", "CONNECTOR")
                if asset_dto.metadata:
                    curr_meta = dict(asset_entity.metadata_json or {})
                    curr_meta.update(asset_dto.metadata)
                    asset_entity.metadata_json = curr_meta
                if acc_id:
                    asset_entity.account_id = acc_id
                asset_entity.updated_at = datetime.utcnow()
                updated += 1
            else:
                # Create new asset
                asset_entity = Asset(
                    user_id=user_id,
                    account_id=acc_id,
                    platform_id=platform_id,
                    asset_type=asset_dto.asset_type,
                    name=asset_dto.name,
                    symbol=asset_dto.symbol,
                    identifier=asset_dto.identifier,
                    quantity=asset_dto.quantity,
                    average_buy_price=asset_dto.average_buy_price,
                    invested_amount=asset_dto.invested_amount,
                    current_price=asset_dto.current_price,
                    current_value=asset_dto.current_value,
                    currency=asset_dto.currency,
                    purchase_date=asset_dto.purchase_date,
                    last_valued_at=datetime.utcnow(),
                    data_source=asset_dto.metadata.get("data_source", "CONNECTOR"),
                    metadata_json=asset_dto.metadata,
                )
                db.add(asset_entity)
                db.flush()
                created += 1

        # --- C. UPSERT TRANSACTIONS ---
        for tx_dto in portfolio.transactions:
            processed += 1
            # Link asset if asset_identifier matches
            linked_asset_id = None
            if tx_dto.asset_identifier:
                asset_lookup = select(Asset).where(
                    Asset.user_id == user_id,
                    (Asset.identifier == tx_dto.asset_identifier) | (Asset.symbol == tx_dto.asset_identifier)
                )
                found_asset = db.execute(asset_lookup).scalars().first()
                if found_asset:
                    linked_asset_id = found_asset.id

            # Check idempotency via external_transaction_id
            if tx_dto.external_transaction_id:
                tx_stmt = select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.external_transaction_id == tx_dto.external_transaction_id,
                )
                existing_tx = db.execute(tx_stmt).scalar_one_or_none()

                if existing_tx:
                    existing_tx.amount = tx_dto.amount
                    existing_tx.price = tx_dto.price
                    existing_tx.quantity = tx_dto.quantity
                    updated += 1
                    continue

            # Insert new transaction
            new_tx = Transaction(
                user_id=user_id,
                asset_id=linked_asset_id,
                transaction_type=tx_dto.transaction_type,
                transaction_date=tx_dto.transaction_date,
                quantity=tx_dto.quantity,
                price=tx_dto.price,
                amount=tx_dto.amount,
                fees=tx_dto.fees,
                taxes=tx_dto.taxes,
                currency=tx_dto.currency,
                external_transaction_id=tx_dto.external_transaction_id,
                transfer_id=tx_dto.transfer_id,
                metadata_json=tx_dto.metadata,
            )
            db.add(new_tx)
            created += 1

        return {"processed": processed, "created": created, "updated": updated}

    @staticmethod
    def _handle_sync_failure(
        connection: Connection,
        sync_log: SyncLog,
        error: ConnectorError,
        db: Session
    ) -> SyncResult:
        now = datetime.utcnow()
        if getattr(error, "code", None) in ("AUTH_FAILED", "TOKEN_EXPIRED"):
            connection.status = "AUTH_REQUIRED"
            connection.last_sync_status = "AUTH_FAILED"
        else:
            connection.status = "SYNC_FAILED"
            connection.last_sync_status = "SYNC_FAILED"

        connection.last_sync_error = error.safe_message

        sync_log.status = SyncStatus.SYNC_FAILED.value
        sync_log.completed_at = now
        sync_log.error_code = error.code
        sync_log.safe_error_message = error.safe_message

        db.commit()

        return SyncResult(
            status="SYNC_FAILED",
            error_code=error.code,
            safe_error_message=error.safe_message,
            completed_at=now,
        )
