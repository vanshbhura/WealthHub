import re
from typing import List, Dict, Any, Optional
from app.imports.mappers.mapping_profiles import FIELD_ALIASES, NORMALIZED_FIELDS
from app.imports.enums import ImportType


class ColumnMapper:
    """
    Automated and user-guided column mapper that matches raw statement
    column headers to WealthHub canonical fields.
    """

    @staticmethod
    def clean_header_name(header: str) -> str:
        """Normalizes header string for comparison: lowercase, removes punctuation & extra spaces."""
        cleaned = re.sub(r"[_\W]+", " ", str(header or "")).strip().lower()
        return cleaned

    @classmethod
    def auto_map_columns(
        cls, headers: List[str], import_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Infers suggested mapping: { raw_header: normalized_field_name }.
        Respects import_type priority (e.g. Bank statements prefer debit/credit).
        """
        mapping: Dict[str, str] = {}
        assigned_targets = set()

        # Step 1: Exact matches to normalized field names or aliases
        for header in headers:
            clean = cls.clean_header_name(header)
            best_target = None

            for target_field, aliases in FIELD_ALIASES.items():
                if target_field in assigned_targets:
                    continue

                if clean == target_field or clean in aliases:
                    best_target = target_field
                    break

            if best_target:
                mapping[header] = best_target
                assigned_targets.add(best_target)

        # Step 2: Substring matches for unmapped headers
        for header in headers:
            if header in mapping:
                continue

            clean = cls.clean_header_name(header)
            best_target = None

            for target_field, aliases in FIELD_ALIASES.items():
                if target_field in assigned_targets:
                    continue

                # Check if alias is inside clean or clean is inside alias
                for alias in aliases:
                    if len(alias) >= 3 and (alias in clean or clean in alias):
                        best_target = target_field
                        break
                if best_target:
                    break

            if best_target:
                mapping[header] = best_target
                assigned_targets.add(best_target)

        return mapping

    @staticmethod
    def extract_mapped_row(
        raw_row: Dict[str, Any], column_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Extracts a dictionary of canonical normalized fields from a raw statement row.
        Includes '__row_number__' from raw_row.
        """
        mapped: Dict[str, Any] = {
            "__row_number__": raw_row.get("__row_number__", 0)
        }

        # Invert mapping: normalized_field -> raw_header
        for raw_header, target_field in column_mapping.items():
            if target_field and target_field in raw_row or raw_header in raw_row:
                val = raw_row.get(raw_header)
                if val is not None and str(val).strip() != "":
                    mapped[target_field] = str(val).strip()

        return mapped
