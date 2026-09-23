import uuid
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.imports.mappers.column_mapper import ColumnMapper
from app.imports.validators.statement_validator import StatementValidator
from app.imports.services.deduplication_service import DeduplicationService
from app.imports.enums import DuplicateStatus, ValidationSeverity, ImportJobStatus


class PreviewService:
    """
    Generates isolated, non-committing statement previews.
    Orchestrates column mapping, row-level validation, deduplication checks,
    and asset/account detection without touching production financial tables.
    """

    @classmethod
    def generate_preview(
        cls,
        user_id: uuid.UUID,
        platform_id: uuid.UUID,
        platform_name: str,
        import_type: str,
        raw_rows: List[Dict[str, Any]],
        column_mapping: Dict[str, str],
        db: Session,
    ) -> Dict[str, Any]:
        # 1. Map raw rows into canonical schema
        mapped_rows = [
            ColumnMapper.extract_mapped_row(raw_row=r, column_mapping=column_mapping)
            for r in raw_rows
        ]

        # 2. Run row-level validation
        norm_rows, issues, counts = StatementValidator.validate_statement(
            mapped_rows=mapped_rows,
            import_type=import_type,
            platform_name=platform_name,
        )

        # 3. Run deduplication
        deduped_rows = DeduplicationService.evaluate_duplicates(
            user_id=user_id,
            platform_id=platform_id,
            normalized_rows=norm_rows,
            db=db,
        )

        # 4. Count new vs duplicate records
        new_cnt = sum(1 for r in deduped_rows if r.get("duplicate_status") == DuplicateStatus.NEW.value and r.get("is_valid"))
        dup_cnt = sum(1 for r in deduped_rows if r.get("duplicate_status") == DuplicateStatus.EXACT_DUPLICATE.value)
        poss_cnt = sum(1 for r in deduped_rows if r.get("duplicate_status") == DuplicateStatus.POSSIBLE_DUPLICATE.value)

        # 5. Detect unique accounts and assets
        accounts_detected = set()
        assets_detected = set()
        for r in deduped_rows:
            acc = r.get("account_number")
            if acc:
                accounts_detected.add(str(acc))
            asset = r.get("asset_name") or r.get("symbol")
            if asset:
                assets_detected.add(str(asset))

        # Overall validation status
        has_blocking_errors = counts["errors"] > 0
        overall_status = (
            ImportJobStatus.INVALID.value if has_blocking_errors else ImportJobStatus.VALID.value
        )

        preview_payload = {
            "status": overall_status,
            "row_count": len(raw_rows),
            "valid_row_count": counts["valid"],
            "warning_count": counts["warnings"],
            "error_count": counts["errors"],
            "new_count": new_cnt,
            "duplicate_count": dup_cnt,
            "possible_duplicate_count": poss_cnt,
            "accounts_detected": sorted(list(accounts_detected)),
            "assets_detected": sorted(list(assets_detected))[:20],  # first 20 for preview
            "issues": issues[:100],  # up to 100 issues for preview display
            "rows": deduped_rows,  # full rows stored in job preview_data
        }

        return preview_payload
