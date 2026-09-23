import uuid
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.snapshot import PortfolioSnapshot
from app.models.asset import Asset
from app.models.account import Account
from app.models.platform import Platform
from app.services.valuation_service import ValuationService
from app.domain.enums import normalize_asset_category


class SnapshotService:
    @staticmethod
    def capture_daily_snapshot(
        user_id: uuid.UUID,
        db: Session,
        snapshot_date: Optional[date] = None
    ) -> PortfolioSnapshot:
        """
        Takes an idempotent snapshot of user's wealth, asset allocation, and platform breakdown.
        Guarantees idempotency: updates existing record if already taken on that date.
        """
        target_date = snapshot_date or date.today()
        wealth_data = ValuationService.calculate_user_wealth(user_id, db)

        # 1. Asset allocation breakdown
        assets = wealth_data["assets"]
        standalone_accounts = wealth_data["standalone_accounts"]

        allocation: Dict[str, float] = {}
        for a in assets:
            cat = normalize_asset_category(a.asset_type).value
            allocation[cat] = round(allocation.get(cat, 0.0) + float(a.current_value or 0.0), 2)

        for acc in standalone_accounts:
            acc_type = acc.account_type.upper()
            cat = "CASH"
            if "FD" in acc_type or "FIXED" in acc_type:
                cat = "FD"
            elif "RD" in acc_type or "RECURRING" in acc_type:
                cat = "RD"
            elif "P2P" in acc_type:
                cat = "P2P"
            allocation[cat] = round(allocation.get(cat, 0.0) + float(acc.current_value or 0.0), 2)

        # 2. Platform values breakdown
        platform_ids = {a.platform_id for a in assets}.union({acc.platform_id for acc in standalone_accounts})
        platform_map = {}
        if platform_ids:
            plat_records = db.execute(select(Platform).where(Platform.id.in_(platform_ids))).scalars().all()
            platform_map = {p.id: p.name for p in plat_records}

        platform_values: Dict[str, float] = {}
        for a in assets:
            p_name = platform_map.get(a.platform_id, "Unknown Platform")
            platform_values[p_name] = round(platform_values.get(p_name, 0.0) + float(a.current_value or 0.0), 2)

        for acc in standalone_accounts:
            p_name = platform_map.get(acc.platform_id, "Unknown Platform")
            platform_values[p_name] = round(platform_values.get(p_name, 0.0) + float(acc.current_value or 0.0), 2)

        # 3. Idempotent Upsert against UniqueConstraint("user_id", "snapshot_date")
        stmt = select(PortfolioSnapshot).where(
            PortfolioSnapshot.user_id == user_id,
            PortfolioSnapshot.snapshot_date == target_date
        )
        existing = db.execute(stmt).scalar_one_or_none()

        if existing:
            existing.total_value = wealth_data["total_wealth"]
            existing.invested_value = wealth_data["invested_value"]
            existing.profit_loss = wealth_data["profit_loss"]
            existing.profit_loss_percentage = wealth_data["profit_loss_percentage"]
            existing.cash_value = wealth_data["cash_value"]
            existing.asset_allocation = allocation
            existing.platform_values = platform_values
            snapshot = existing
        else:
            snapshot = PortfolioSnapshot(
                user_id=user_id,
                snapshot_date=target_date,
                total_value=wealth_data["total_wealth"],
                invested_value=wealth_data["invested_value"],
                profit_loss=wealth_data["profit_loss"],
                profit_loss_percentage=wealth_data["profit_loss_percentage"],
                cash_value=wealth_data["cash_value"],
                asset_allocation=allocation,
                platform_values=platform_values
            )
            db.add(snapshot)

        db.commit()
        db.refresh(snapshot)
        return snapshot

    @staticmethod
    def get_snapshots(
        user_id: uuid.UUID,
        period: str = "1M",
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Fetch snapshots filtered by timeframe: 1M, 2M, 6M, 12M, 24M, 5Y.
        Returns actual chronological database snapshots.
        Never fabricates fake points.
        """
        today = date.today()
        days_map = {
            "1M": 30,
            "2M": 60,
            "6M": 180,
            "12M": 365,
            "24M": 730,
            "5Y": 1825,
        }
        days = days_map.get(str(period).upper(), 30)
        start_date = today - timedelta(days=days)

        stmt = (
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_date >= start_date
            )
            .order_by(PortfolioSnapshot.snapshot_date.asc())
        )
        snapshots = list(db.execute(stmt).scalars().all())

        # Insufficient history check: requires at least 2 snapshots to show a trend
        has_sufficient_history = len(snapshots) >= 2

        formatted = [
            {
                "id": s.id,
                "date": s.snapshot_date.isoformat(),
                "snapshot_date": s.snapshot_date,
                "value": s.total_value,
                "total_value": s.total_value,
                "invested_value": s.invested_value,
                "profit_loss": s.profit_loss,
                "profit_loss_percentage": s.profit_loss_percentage,
                "cash_value": s.cash_value,
                "asset_allocation": s.asset_allocation or {},
                "platform_values": s.platform_values or {},
                "created_at": s.created_at
            }
            for s in snapshots
        ]

        return {
            "period": str(period).upper(),
            "has_sufficient_history": has_sufficient_history,
            "data_points_count": len(formatted),
            "snapshots": formatted
        }
