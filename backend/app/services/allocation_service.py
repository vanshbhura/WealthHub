import uuid
from typing import List, Dict, Any
from collections import defaultdict
from app.domain.enums import normalize_asset_category, AssetCategory
from app.domain.portfolio import AllocationSliceDomain


class AllocationService:
    @staticmethod
    def calculate_allocation(
        items: List[Dict[str, Any]],
        group_key: str,
        total_basis: float,
        label_key: str = None
    ) -> List[AllocationSliceDomain]:
        """
        Groups items by key and computes absolute value and percentage of total_basis.
        Percentages sum strictly to 100.0% when total_basis > 0.
        """
        if total_basis <= 0 or not items:
            return []

        grouped = defaultdict(float)
        labels = {}

        for item in items:
            val = max(0.0, float(item.get("current_value", 0.0)))
            k = str(item.get(group_key, "OTHER"))
            lbl = str(item.get(label_key, k)) if label_key else k
            grouped[k] += val
            labels[k] = lbl

        slices: List[AllocationSliceDomain] = []
        for k, val in sorted(grouped.items(), key=lambda x: x[1], reverse=True):
            pct = (val / total_basis) * 100.0
            slices.append(AllocationSliceDomain(
                key=k,
                label=labels.get(k, k),
                value=round(val, 2),
                percentage=round(pct, 2)
            ))

        return slices

    @staticmethod
    def calculate_asset_type_allocation(
        assets: List[Any],
        standalone_accounts: List[Any],
        total_wealth: float
    ) -> List[AllocationSliceDomain]:
        """
        Computes portfolio allocation across normalized asset categories.
        """
        items = []
        for a in assets:
            cat = normalize_asset_category(getattr(a, "asset_type", "OTHER"))
            items.append({
                "category": cat.value,
                "label": cat.value.replace("_", " ").title(),
                "current_value": getattr(a, "current_value", 0.0)
            })

        for acc in standalone_accounts:
            acc_type = getattr(acc, "account_type", "CASH").upper()
            cat = AssetCategory.CASH
            if "FD" in acc_type or "FIXED" in acc_type:
                cat = AssetCategory.FD
            elif "RD" in acc_type or "RECURRING" in acc_type:
                cat = AssetCategory.RD
            elif "P2P" in acc_type:
                cat = AssetCategory.P2P

            items.append({
                "category": cat.value,
                "label": cat.value.replace("_", " ").title(),
                "current_value": getattr(acc, "current_value", 0.0)
            })

        return AllocationService.calculate_allocation(
            items=items,
            group_key="category",
            label_key="label",
            total_basis=total_wealth
        )

    @staticmethod
    def calculate_platform_allocation(
        platform_breakdown: List[Dict[str, Any]],
        total_wealth: float
    ) -> List[AllocationSliceDomain]:
        """
        Computes portfolio allocation across platforms.
        """
        items = []
        for p in platform_breakdown:
            items.append({
                "platform_id": str(p["platform_id"]),
                "platform_name": p["platform_name"],
                "current_value": p["current_value"]
            })

        return AllocationService.calculate_allocation(
            items=items,
            group_key="platform_id",
            label_key="platform_name",
            total_basis=total_wealth
        )
