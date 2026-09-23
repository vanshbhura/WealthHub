import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.asset import Asset
from app.models.platform import Platform
from app.models.transaction import Transaction
from app.connectors.dtos import NormalizedPortfolio, NormalizedHolding, NormalizedTransaction


class DeduplicationEngine:
    """
    Source-aware deduplication and double-counting protection engine.
    Detects cross-platform overlapping securities (e.g. CDSL/NSDL depository vs Groww/Zerodha broker)
    using universal identifiers (ISIN), symbols, and transaction fingerprints.
    """

    @staticmethod
    def flag_overlapping_holdings(
        user_id: uuid.UUID,
        platform_id: uuid.UUID,
        portfolio: NormalizedPortfolio,
        db: Session,
    ) -> Dict[str, Any]:
        """
        Inspects incoming holdings against existing assets for the user across all other platforms.
        If an identical security (e.g., ISIN) already exists in a primary broker or import,
        flags the incoming holding as a duplicate to protect from double counting.
        """
        # Fetch all existing assets for this user from other platforms
        stmt = (
            select(Asset, Platform.name.label("platform_name"))
            .join(Platform, Platform.id == Asset.platform_id)
            .where(
                Asset.user_id == user_id,
                Asset.platform_id != platform_id,
            )
        )
        existing_records = db.execute(stmt).all()

        # Build lookup indices for existing assets
        isin_to_asset: Dict[str, Any] = {}
        symbol_to_asset: Dict[tuple, Any] = {}

        for row in existing_records:
            asset = row[0]
            plat_name = row[1]
            if asset.identifier:
                isin_to_asset[asset.identifier.strip().upper()] = (asset, plat_name)
            if asset.symbol and asset.asset_type:
                key = (asset.symbol.strip().upper(), asset.asset_type.strip().upper())
                symbol_to_asset[key] = (asset, plat_name)

        flagged_count = 0

        for holding in portfolio.holdings:
            asset_dto = holding.asset
            incoming_isin = asset_dto.identifier.strip().upper() if asset_dto.identifier else None
            incoming_symbol_key = (
                (asset_dto.symbol.strip().upper(), asset_dto.asset_type.strip().upper())
                if asset_dto.symbol and asset_dto.asset_type
                else None
            )

            matched_asset = None
            matched_plat = None

            if incoming_isin and incoming_isin in isin_to_asset:
                matched_asset, matched_plat = isin_to_asset[incoming_isin]
            elif incoming_symbol_key and incoming_symbol_key in symbol_to_asset:
                matched_asset, matched_plat = symbol_to_asset[incoming_symbol_key]

            if matched_asset:
                flagged_count += 1
                asset_dto.metadata["is_duplicate"] = True
                asset_dto.metadata["source_overlap"] = True
                asset_dto.metadata["duplicate_reason"] = (
                    f"Overlaps with holding '{matched_asset.name}' in {matched_plat} (ISIN: {matched_asset.identifier or matched_asset.symbol})."
                )
                asset_dto.metadata["canonical_asset_id"] = str(matched_asset.id)
                asset_dto.metadata["canonical_platform_id"] = str(matched_asset.platform_id)

        return {
            "flagged_duplicates": flagged_count,
            "total_holdings": len(portfolio.holdings),
        }

    @staticmethod
    def deduplicate_transactions(
        user_id: uuid.UUID,
        transactions: List[NormalizedTransaction],
        db: Session,
    ) -> List[NormalizedTransaction]:
        """
        Filters out transactions that already exist in the database by external_transaction_id.
        """
        if not transactions:
            return []

        ext_ids = [t.external_transaction_id for t in transactions if t.external_transaction_id]
        existing_ids = set()
        if ext_ids:
            stmt = select(Transaction.external_transaction_id).where(
                Transaction.user_id == user_id,
                Transaction.external_transaction_id.in_(ext_ids),
            )
            existing_ids = set(db.execute(stmt).scalars().all())

        return [t for t in transactions if not t.external_transaction_id or t.external_transaction_id not in existing_ids]
