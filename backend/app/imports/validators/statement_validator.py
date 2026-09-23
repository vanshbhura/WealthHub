from typing import List, Dict, Any, Tuple
from app.imports.enums import ValidationSeverity
from app.imports.validators.row_validator import RowValidator


class StatementValidator:
    """
    Validates all rows of a mapped statement, aggregating row-level and statement-level issues.
    """

    @classmethod
    def validate_statement(
        cls,
        mapped_rows: List[Dict[str, Any]],
        import_type: str,
        platform_name: str = "",
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
        """
        Returns:
        - normalized_rows: list of normalized row dictionaries
        - all_issues: list of validation issues
        - summary_counts: { "total": int, "valid": int, "errors": int, "warnings": int, "info": int }
        """
        normalized_rows: List[Dict[str, Any]] = []
        all_issues: List[Dict[str, Any]] = []

        errors_count = 0
        warnings_count = 0
        info_count = 0
        valid_rows_count = 0

        for r in mapped_rows:
            norm_r, issues = RowValidator.validate_row(
                mapped_row=r,
                import_type=import_type,
                platform_name=platform_name,
            )
            normalized_rows.append(norm_r)
            all_issues.extend(issues)

            has_error = False
            for iss in issues:
                sev = iss.get("severity")
                if sev == ValidationSeverity.ERROR.value:
                    has_error = True
                    errors_count += 1
                elif sev == ValidationSeverity.WARNING.value:
                    warnings_count += 1
                elif sev == ValidationSeverity.INFO.value:
                    info_count += 1

            if not has_error:
                valid_rows_count += 1

        summary_counts = {
            "total": len(mapped_rows),
            "valid": valid_rows_count,
            "errors": errors_count,
            "warnings": warnings_count,
            "info": info_count,
        }

        return normalized_rows, all_issues, summary_counts
