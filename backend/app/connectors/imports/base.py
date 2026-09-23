from typing import Any, Dict, List, Optional
import uuid
from app.connectors.base import BaseConnector
from app.connectors.enums import ConnectorType, ConnectionMethodStatus
from app.connectors.dtos import NormalizedPortfolio


class ImportConnector(BaseConnector):
    """
    Production architecture for financial statement parsing (CSV, Excel, PDF).
    Integrates directly with WealthHub's canonical connector pipeline.
    """
    connector_type = ConnectorType.IMPORT
    connector_key = "statement_import"
    name = "Statement Import"
    status = ConnectionMethodStatus.AVAILABLE

    supports_holdings = True
    supports_transactions = True
    supports_balances = True
    supports_orders = False
    supports_statements = True

    async def validate_file(self, file_bytes: bytes, filename: str) -> str:
        """Validates file format, size, and security constraints."""
        from app.imports.services.import_service import ImportService
        return ImportService.validate_file_security(filename=filename, file_bytes=file_bytes)

    async def parse(self, file_bytes: bytes, filename: str) -> Any:
        """Extracts tabular records from raw statement bytes."""
        from app.imports.services.import_service import ImportService
        from app.imports.parsers import get_parser_for_file_type
        file_type = ImportService.validate_file_security(filename=filename, file_bytes=file_bytes)
        parser = get_parser_for_file_type(file_type)
        return parser.parse_bytes(file_bytes=file_bytes, filename=filename)

    async def preview(
        self,
        user_id: uuid.UUID,
        platform_id: uuid.UUID,
        platform_name: str,
        import_type: str,
        raw_rows: List[Dict[str, Any]],
        column_mapping: Dict[str, str],
        db,
    ) -> Dict[str, Any]:
        """Provides dry-run preview and row-level validation before committing."""
        from app.imports.services.preview_service import PreviewService
        return PreviewService.generate_preview(
            user_id=user_id,
            platform_id=platform_id,
            platform_name=platform_name,
            import_type=import_type,
            raw_rows=raw_rows,
            column_mapping=column_mapping,
            db=db,
        )

    async def commit_job(
        self,
        import_job_id: uuid.UUID,
        user_id: uuid.UUID,
        db,
    ) -> Dict[str, Any]:
        """Commits normalized statement records into database inside atomic transaction."""
        from app.imports.services.commit_service import CommitService
        return CommitService.commit_import_job(
            import_job_id=import_job_id,
            user_id=user_id,
            db=db,
        )
