import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.platform import Platform
from app.models.connection import Connection
from app.models.account import Account
from app.models.asset import Asset
from app.models.transaction import Transaction, TransactionType
from app.models.snapshot import PortfolioSnapshot
from app.services.valuation_service import ValuationService
from app.services.pnl_service import PnlService
from app.services.performance_service import PerformanceService
from app.services.allocation_service import AllocationService
from app.domain.enums import normalize_asset_category, DataFreshnessStatus, AssetCategory


class PortfolioService:
    @staticmethod
    def calculate_invested_value_from_records(user_id: uuid.UUID, db: Session) -> float:
        """
        Calculates total invested capital across user assets, accounts, and transactions.
        Accurately handles internal transfers (TRANSFER_IN and TRANSFER_OUT matching transfer_id)
        to prevent double-counting capital moved between connected accounts.
        """
        # 1. Fetch transactions for user
        tx_stmt = select(Transaction).where(Transaction.user_id == user_id)
        transactions = list(db.execute(tx_stmt).scalars().all())

        # Net out internal transfers by transfer_id
        transfer_totals: Dict[str, float] = {}
        for tx in transactions:
            if tx.transfer_id:
                if tx.transaction_type == TransactionType.TRANSFER_IN:
                    transfer_totals[tx.transfer_id] = transfer_totals.get(tx.transfer_id, 0.0) + tx.amount
                elif tx.transaction_type == TransactionType.TRANSFER_OUT:
                    transfer_totals[tx.transfer_id] = transfer_totals.get(tx.transfer_id, 0.0) - tx.amount

        # Internal transfers that match sum to ~0 and are excluded from external capital additions
        # Assets and Accounts
        asset_stmt = select(Asset).where(Asset.user_id == user_id)
        assets = list(db.execute(asset_stmt).scalars().all())
        linked_account_ids = {a.account_id for a in assets if a.account_id is not None}

        account_stmt = select(Account).where(Account.user_id == user_id)
        accounts = list(db.execute(account_stmt).scalars().all())
        standalone_accounts = [acc for acc in accounts if acc.id not in linked_account_ids]

        total_invested = sum(max(0.0, float(a.invested_amount or 0.0)) for a in assets)
        total_invested += sum(max(0.0, float(acc.invested_value or 0.0)) for acc in standalone_accounts)

        return round(total_invested, 2)

    @staticmethod
    def get_summary(user_id: uuid.UUID, db: Session) -> dict:
        """
        Returns the consolidated portfolio summary conforming to Section 22.
        """
        wealth_data = ValuationService.calculate_user_wealth(user_id, db)
        today_change, today_change_pct = ValuationService.calculate_today_change(
            user_id=user_id,
            current_total=wealth_data["total_wealth"],
            db=db
        )

        # Check historical snapshots existence
        hist_count_stmt = select(PortfolioSnapshot).where(PortfolioSnapshot.user_id == user_id)
        snapshots_count = len(list(db.execute(hist_count_stmt).scalars().all()))

        # Distinct platforms count
        assets = wealth_data["assets"]
        standalone_accounts = wealth_data["standalone_accounts"]
        platform_ids = {a.platform_id for a in assets}.union({acc.platform_id for acc in standalone_accounts})

        has_realtime = wealth_data["overall_freshness"] == DataFreshnessStatus.REALTIME

        return {
            "total_wealth": wealth_data["total_wealth"],
            "invested_value": wealth_data["invested_value"],
            "profit_loss": wealth_data["profit_loss"],
            "profit_loss_percentage": wealth_data["profit_loss_percentage"],
            "today_change": today_change,
            "today_change_percentage": today_change_pct,
            "cash_value": wealth_data["cash_value"],
            "currency": "INR",
            "asset_count": wealth_data["asset_count"],
            "platform_count": len(platform_ids),
            "last_updated": datetime.utcnow(),
            "data_freshness": wealth_data["overall_freshness"].value,
            "data_quality": {
                "has_historical_data": snapshots_count >= 2,
                "has_realtime_data": has_realtime,
                "historical_snapshot_count": snapshots_count
            }
        }

    @staticmethod
    def get_platform_breakdown(user_id: uuid.UUID, db: Session) -> List[Dict[str, Any]]:
        """
        Returns aggregated platform breakdown conforming to Section 8 & Section 23.
        """
        conn_stmt = select(Connection).where(Connection.user_id == user_id)
        connections = list(db.execute(conn_stmt).scalars().all())
        conn_by_platform = {c.platform_id: c for c in connections}

        asset_stmt = select(Asset).where(Asset.user_id == user_id)
        assets = list(db.execute(asset_stmt).scalars().all())

        account_stmt = select(Account).where(Account.user_id == user_id)
        accounts = list(db.execute(account_stmt).scalars().all())

        platform_ids = set(conn_by_platform.keys())
        for a in assets:
            platform_ids.add(a.platform_id)
        for acc in accounts:
            platform_ids.add(acc.platform_id)

        if not platform_ids:
            return []

        plat_stmt = select(Platform).where(Platform.id.in_(platform_ids))
        platforms = list(db.execute(plat_stmt).scalars().all())
        plat_map = {p.id: p for p in platforms}

        breakdown = []
        for pid in platform_ids:
            plat = plat_map.get(pid)
            if not plat:
                continue

            conn = conn_by_platform.get(pid)
            plat_assets = [a for a in assets if a.platform_id == pid]
            plat_accounts = [acc for acc in accounts if acc.platform_id == pid]

            linked_acc_ids = {a.account_id for a in plat_assets if a.account_id is not None}
            standalone_accounts = [acc for acc in plat_accounts if acc.id not in linked_acc_ids]

            current_val = sum(max(0.0, float(a.current_value or 0.0)) for a in plat_assets) + \
                          sum(max(0.0, float(acc.current_value or 0.0)) for acc in standalone_accounts)
            invested_val = sum(max(0.0, float(a.invested_amount or 0.0)) for a in plat_assets) + \
                           sum(max(0.0, float(acc.invested_value or 0.0)) for acc in standalone_accounts)

            pnl, pnl_pct = PnlService.calculate(current_val, invested_val)

            # Determine platform freshness
            freshness_statuses = [
                ValuationService.determine_freshness(a.last_valued_at, a.data_source)
                for a in plat_assets if a.last_valued_at
            ]
            if conn and conn.last_synced_at:
                freshness_statuses.append(ValuationService.determine_freshness(conn.last_synced_at, plat.integration_type))

            if any(f == DataFreshnessStatus.REALTIME for f in freshness_statuses):
                plat_freshness = DataFreshnessStatus.REALTIME
            elif any(f == DataFreshnessStatus.RECENT for f in freshness_statuses):
                plat_freshness = DataFreshnessStatus.RECENT
            elif any(f == DataFreshnessStatus.TODAY for f in freshness_statuses):
                plat_freshness = DataFreshnessStatus.TODAY
            elif freshness_statuses:
                plat_freshness = DataFreshnessStatus.STALE
            else:
                plat_freshness = DataFreshnessStatus.UNKNOWN

            breakdown.append({
                "platform_id": plat.id,
                "connection_id": conn.id if conn else None,
                "platform_name": plat.name,
                "platform_slug": plat.slug,
                "category": plat.category,
                "integration_type": plat.integration_type,
                "logo_url": plat.logo_url,
                "status": conn.status if conn else "CONNECTED",
                "current_value": round(current_val, 2),
                "invested_value": round(invested_val, 2),
                "profit_loss": pnl,
                "profit_loss_percentage": pnl_pct,
                "asset_count": len(plat_assets) + len(standalone_accounts),
                "holdings_count": len(plat_assets),
                "last_updated": conn.last_synced_at if conn else (plat_assets[0].last_valued_at if plat_assets else None),
                "freshness_status": plat_freshness.value
            })

        breakdown.sort(key=lambda x: x["current_value"], reverse=True)
        return breakdown

    @staticmethod
    def get_assets_calculated(
        user_id: uuid.UUID,
        db: Session,
        platform_id: Optional[uuid.UUID] = None,
        asset_type: Optional[str] = None,
        account_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Returns normalized calculated asset data with filters conforming to Section 9 & Section 24.
        """
        stmt = select(Asset).where(Asset.user_id == user_id)
        if platform_id:
            stmt = stmt.where(Asset.platform_id == platform_id)
        if asset_type:
            cat = normalize_asset_category(asset_type)
            stmt = stmt.where(Asset.asset_type.in_([asset_type.upper(), cat.value, f"{cat.value}S"]))
        if account_id:
            stmt = stmt.where(Asset.account_id == account_id)

        assets = list(db.execute(stmt).scalars().all())
        if not assets:
            return []

        # Platform names
        plat_ids = {a.platform_id for a in assets}
        plats = db.execute(select(Platform).where(Platform.id.in_(plat_ids))).scalars().all()
        plat_map = {p.id: p.name for p in plats}

        calculated_list = []
        for a in assets:
            val_info = ValuationService.value_individual_asset(a)
            calculated_list.append({
                "id": a.id,
                "user_id": a.user_id,
                "platform_id": a.platform_id,
                "platform_name": plat_map.get(a.platform_id, "Unknown Platform"),
                "account_id": a.account_id,
                "name": a.name,
                "symbol": a.symbol,
                "asset_type": val_info.get("asset_type", a.asset_type),
                "quantity": val_info.get("quantity", a.quantity),
                "average_buy_price": val_info.get("average_buy_price", a.average_buy_price),
                "invested_value": val_info.get("invested_value", a.invested_amount),
                "current_price": val_info.get("current_price", a.current_price),
                "current_value": val_info.get("current_value", a.current_value),
                "profit_loss": val_info.get("profit_loss", 0.0),
                "profit_loss_percentage": val_info.get("profit_loss_percentage"),
                "last_valued_at": a.last_valued_at,
                "data_source": a.data_source,
                "freshness_status": val_info.get("freshness_status", DataFreshnessStatus.UNKNOWN).value,
                "currency": a.currency,
                "p2p_details": val_info.get("p2p_details"),
                "precious_metal_details": val_info.get("precious_metal_details")
            })

        calculated_list.sort(key=lambda x: x["current_value"], reverse=True)
        return calculated_list

    @staticmethod
    def get_portfolio_allocation(user_id: uuid.UUID, db: Session) -> Dict[str, Any]:
        """
        Returns portfolio allocation by asset type and platform conforming to Section 21.
        """
        wealth_data = ValuationService.calculate_user_wealth(user_id, db)
        total_wealth = wealth_data["total_wealth"]

        by_asset_type = AllocationService.calculate_asset_type_allocation(
            assets=wealth_data["assets"],
            standalone_accounts=wealth_data["standalone_accounts"],
            total_wealth=total_wealth
        )

        platforms_breakdown = PortfolioService.get_platform_breakdown(user_id, db)
        by_platform = AllocationService.calculate_platform_allocation(
            platform_breakdown=platforms_breakdown,
            total_wealth=total_wealth
        )

        return {
            "total_basis": total_wealth,
            "by_asset_type": [
                {"key": s.key, "label": s.label, "value": s.value, "percentage": s.percentage}
                for s in by_asset_type
            ],
            "by_platform": [
                {"key": s.key, "label": s.label, "value": s.value, "percentage": s.percentage}
                for s in by_platform
            ]
        }
