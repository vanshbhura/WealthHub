import uuid
from datetime import datetime, date, timedelta
from typing import Tuple, Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.asset import Asset
from app.models.account import Account
from app.models.snapshot import PortfolioSnapshot
from app.domain.enums import (
    AssetCategory,
    DataFreshnessStatus,
    DataSource,
    normalize_asset_category,
)
from app.domain.calculations import (
    calculate_pnl,
    calculate_daily_movement,
    calculate_quantity_valuation,
    calculate_precious_metal_valuation,
    calculate_p2p_position,
)
from app.domain.money import safe_round
from app.services.pnl_service import PnlService
from app.services.performance_service import PerformanceService


class ValuationService:
    @staticmethod
    def determine_freshness(last_valued_at: Optional[datetime], data_source: str = "MANUAL") -> DataFreshnessStatus:
        """
        Determines the data freshness status based on timestamp and source.
        Only marks REALTIME if from an active automated source within 15 minutes.
        """
        if not last_valued_at:
            return DataFreshnessStatus.UNKNOWN

        now = datetime.utcnow()
        diff = now - last_valued_at

        # Never claim realtime unless source actually supports it
        is_live_api = str(data_source).upper() in ("BROKER_API", "AA", "PROVIDER_API", "OAUTH")

        if is_live_api and diff.total_seconds() <= 900:  # 15 mins
            return DataFreshnessStatus.REALTIME
        elif diff.total_seconds() <= 86400:  # 24 hours
            return DataFreshnessStatus.RECENT
        elif last_valued_at.date() == date.today():
            return DataFreshnessStatus.TODAY
        else:
            return DataFreshnessStatus.STALE

    @staticmethod
    def value_individual_asset(asset: Asset) -> Dict[str, Any]:
        """
        Applies asset-specific valuation rules depending on asset class.
        """
        cat = normalize_asset_category(asset.asset_type)
        meta = asset.metadata_json or {}

        # 1. Quantity-based assets: Stocks, ETFs, Mutual Funds, Crypto
        if cat in (AssetCategory.STOCK, AssetCategory.ETF, AssetCategory.MUTUAL_FUND, AssetCategory.CRYPTO):
            res = calculate_quantity_valuation(
                quantity=asset.quantity,
                current_price=asset.current_price,
                average_buy_price=asset.average_buy_price,
                reported_invested=asset.invested_amount
            )
            res["asset_type"] = cat.value
            res["freshness_status"] = ValuationService.determine_freshness(asset.last_valued_at, asset.data_source)
            return res

        # 2. Precious Metals: Digital/Physical Gold & Silver, SGB
        elif cat in (AssetCategory.DIGITAL_GOLD, AssetCategory.DIGITAL_SILVER,
                     AssetCategory.PHYSICAL_GOLD, AssetCategory.PHYSICAL_SILVER, AssetCategory.SGB):
            res = calculate_precious_metal_valuation(
                quantity_in_grams=asset.quantity,
                current_price_per_gram=asset.current_price,
                average_buy_price_per_gram=asset.average_buy_price,
                reported_invested=asset.invested_amount
            )
            res["asset_type"] = cat.value
            res["precious_metal_details"] = {
                "metal": "GOLD" if "GOLD" in cat.value or cat == AssetCategory.SGB else "SILVER",
                "grams": asset.quantity,
                "price_per_gram": asset.current_price
            }
            res["freshness_status"] = ValuationService.determine_freshness(asset.last_valued_at, asset.data_source)
            return res

        # 3. P2P Loans
        elif cat == AssetCategory.P2P:
            principal_inv = asset.invested_amount or meta.get("principal_invested", 0.0)
            principal_out = meta.get("principal_outstanding", asset.current_value or principal_inv)
            res = calculate_p2p_position(
                principal_invested=principal_inv,
                principal_outstanding=principal_out,
                interest_earned=meta.get("interest_earned"),
                interest_received=meta.get("interest_received"),
                repayments=meta.get("repayments"),
                overdue_amount=meta.get("overdue_amount"),
                write_offs=meta.get("write_offs")
            )
            res["asset_type"] = cat.value
            res["p2p_details"] = {
                "principal_invested": res["principal_invested"],
                "principal_outstanding": res["principal_outstanding"],
                "interest_earned": res["interest_earned"],
                "interest_received": res["interest_received"],
                "repayments": res["repayments"],
                "overdue_amount": res["overdue_amount"],
                "write_offs": res["write_offs"]
            }
            res["freshness_status"] = ValuationService.determine_freshness(asset.last_valued_at, asset.data_source)
            return res

        # 4. Deposit & Term assets: FD, RD, Cash, EPF, PPF, NPS, Real Estate, Bonds, Other
        else:
            invested = max(0.0, float(asset.invested_amount or 0.0))
            current = max(0.0, float(asset.current_value or 0.0)) if asset.current_value > 0 else invested
            pnl, pnl_pct = calculate_pnl(current, invested)
            return {
                "quantity": asset.quantity,
                "average_buy_price": asset.average_buy_price,
                "invested_value": invested,
                "current_price": asset.current_price,
                "current_value": current,
                "profit_loss": pnl,
                "profit_loss_percentage": pnl_pct,
                "asset_type": cat.value,
                "freshness_status": ValuationService.determine_freshness(asset.last_valued_at, asset.data_source)
            }

    @staticmethod
    def calculate_user_wealth(user_id: uuid.UUID, db: Session) -> dict:
        """
        Calculates user's total wealth, invested amount, and profit/loss.
        Prevents double-counting:
        - If an Account has individual Assets linked, the assets represent the underlying value.
        - If an Account has no individual Assets, the account's own current_value is included.
        """
        asset_stmt = select(Asset).where(Asset.user_id == user_id)
        assets = list(db.execute(asset_stmt).scalars().all())
        linked_account_ids = {a.account_id for a in assets if a.account_id is not None}

        account_stmt = select(Account).where(Account.user_id == user_id)
        accounts = list(db.execute(account_stmt).scalars().all())

        # Double-counting protection: exclude flagged duplicates/overlapping assets from valuation
        active_assets = [
            a for a in assets
            if not (a.metadata_json and (a.metadata_json.get("is_duplicate") is True or a.metadata_json.get("source_overlap") is True))
        ]
        duplicate_assets = [
            a for a in assets
            if (a.metadata_json and (a.metadata_json.get("is_duplicate") is True or a.metadata_json.get("source_overlap") is True))
        ]

        assets_current = sum(max(0.0, float(a.current_value or 0.0)) for a in active_assets)
        assets_invested = sum(max(0.0, float(a.invested_amount or 0.0)) for a in active_assets)

        standalone_accounts = [acc for acc in accounts if acc.id not in linked_account_ids]
        standalone_current = sum(max(0.0, float(acc.current_value or 0.0)) for acc in standalone_accounts)
        standalone_invested = sum(max(0.0, float(acc.invested_value or 0.0)) for acc in standalone_accounts)

        total_wealth = round(assets_current + standalone_current, 2)
        total_invested = round(assets_invested + standalone_invested, 2)

        # Use PnlService for safe division (null if invested == 0)
        profit_loss, profit_loss_pct = PnlService.calculate(total_wealth, total_invested)

        # Cash value: CASH, SAVINGS, FD, RD (only active non-duplicate assets)
        cash_value = sum(
            a.current_value for a in active_assets
            if normalize_asset_category(a.asset_type) in (AssetCategory.CASH, AssetCategory.FD, AssetCategory.RD)
        ) + sum(
            acc.current_value for acc in standalone_accounts
            if any(k in acc.account_type.upper() for k in ("SAVING", "CURRENT", "CASH", "DEPOSIT", "FD", "RD"))
        )

        # Freshness of overall portfolio
        freshness_list = [
            ValuationService.determine_freshness(a.last_valued_at, a.data_source)
            for a in active_assets if a.last_valued_at
        ]
        if any(f == DataFreshnessStatus.REALTIME for f in freshness_list):
            overall_freshness = DataFreshnessStatus.REALTIME
        elif any(f == DataFreshnessStatus.RECENT for f in freshness_list):
            overall_freshness = DataFreshnessStatus.RECENT
        elif any(f == DataFreshnessStatus.TODAY for f in freshness_list):
            overall_freshness = DataFreshnessStatus.TODAY
        elif freshness_list:
            overall_freshness = DataFreshnessStatus.STALE
        else:
            overall_freshness = DataFreshnessStatus.UNKNOWN

        return {
            "total_wealth": total_wealth,
            "invested_value": total_invested,
            "profit_loss": profit_loss,
            "profit_loss_percentage": profit_loss_pct,
            "cash_value": round(cash_value, 2),
            "asset_count": len(active_assets) + len(standalone_accounts),
            "duplicate_count": len(duplicate_assets),
            "overall_freshness": overall_freshness,
            "assets": active_assets,
            "standalone_accounts": standalone_accounts,
            "flagged_duplicates": [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "reason": d.metadata_json.get("duplicate_reason"),
                    "identifier": d.identifier or d.symbol,
                }
                for d in duplicate_assets
            ],
        }

    @staticmethod
    def calculate_today_change(
        user_id: uuid.UUID,
        current_total: float,
        db: Session
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculates daily movement based on prior portfolio snapshot.
        If no prior snapshot exists, returns (None, None).
        """
        today = date.today()
        stmt = (
            select(PortfolioSnapshot)
            .where(
                PortfolioSnapshot.user_id == user_id,
                PortfolioSnapshot.snapshot_date < today
            )
            .order_by(desc(PortfolioSnapshot.snapshot_date))
            .limit(1)
        )
        previous_snapshot = db.execute(stmt).scalar_one_or_none()
        if not previous_snapshot:
            return None, None

        return PerformanceService.calculate_daily_change(current_total, previous_snapshot.total_value)
