import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.import_job import ImportJob
from app.models.platform import Platform
from app.imports.enums import ImportJobStatus, ImportType
from app.imports.exceptions import (
    FileSecurityError,
    ParseError,
    ValidationError,
    ImportError,
)
from app.imports.parsers import get_parser_for_file_type
from app.imports.mappers.column_mapper import ColumnMapper
from app.imports.services.preview_service import PreviewService
from app.imports.services.commit_service import CommitService

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".pdf"}


class ImportService:
    """
    Main orchestrator for the WealthHub statement import subsystem.
    Enforces security, manages import job sessions, handles parsing,
    preview revalidation, and atomic commits.
    """

    @classmethod
    def validate_file_security(cls, filename: str, file_bytes: bytes) -> str:
        """Validates file extension, size, and returns normalized file type (CSV, XLSX, PDF)."""
        if not filename or not filename.strip():
            raise FileSecurityError("Filename is missing.")

        clean_name = os.path.basename(filename.strip())
        _, ext = os.path.splitext(clean_name)
        ext = ext.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise FileSecurityError(
                f"Unsupported file format '{ext}'. Supported formats: CSV, XLSX, PDF."
            )

        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise FileSecurityError(
                f"File size exceeds the 15 MB maximum limit ({len(file_bytes) / 1024 / 1024:.1f} MB)."
            )

        if len(file_bytes) == 0:
            raise FileSecurityError("Uploaded file is empty.")

        if ext == ".csv":
            return "CSV"
        elif ext in (".xlsx", ".xls"):
            return "XLSX"
        elif ext == ".pdf":
            return "PDF"
        return "UNKNOWN"

    @classmethod
    def create_import_job(
        cls,
        user_id: uuid.UUID,
        platform_id: uuid.UUID,
        import_type: str,
        file_bytes: bytes,
        filename: str,
        db: Session,
    ) -> ImportJob:
        # 1. Security & Validation
        file_type = cls.validate_file_security(filename, file_bytes)

        plat_stmt = select(Platform).where(Platform.id == platform_id)
        platform = db.execute(plat_stmt).scalar_one_or_none()
        if not platform:
            raise ValidationError(f"Platform with ID '{platform_id}' does not exist.")

        # 2. Parse file
        parser = get_parser_for_file_type(file_type)
        headers, raw_rows = parser.parse_bytes(file_bytes=file_bytes, filename=filename)

        # 3. Auto-suggest column mapping
        column_mapping = ColumnMapper.auto_map_columns(headers, import_type=import_type)

        # 4. Generate initial preview and validation
        preview_payload = PreviewService.generate_preview(
            user_id=user_id,
            platform_id=platform.id,
            platform_name=platform.name,
            import_type=import_type,
            raw_rows=raw_rows,
            column_mapping=column_mapping,
            db=db,
        )

        # 5. Persist ImportJob
        job = ImportJob(
            id=uuid.uuid4(),
            user_id=user_id,
            platform_id=platform.id,
            import_type=import_type,
            file_name=os.path.basename(filename),
            file_type=file_type,
            file_size=len(file_bytes),
            status=preview_payload["status"],
            row_count=preview_payload["row_count"],
            valid_row_count=preview_payload["valid_row_count"],
            warning_count=preview_payload["warning_count"],
            error_count=preview_payload["error_count"],
            new_count=preview_payload["new_count"],
            duplicate_count=preview_payload["duplicate_count"],
            possible_duplicate_count=preview_payload["possible_duplicate_count"],
            column_mapping=column_mapping,
            preview_data={
                "headers": headers,
                "raw_rows": raw_rows[:2000],  # store up to 2000 raw rows for re-mapping
                **preview_payload,
            },
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        return job

    @classmethod
    def get_job_or_raise(
        cls, job_id: uuid.UUID, user_id: uuid.UUID, db: Session
    ) -> ImportJob:
        stmt = select(ImportJob).where(
            ImportJob.id == job_id, ImportJob.user_id == user_id
        )
        job = db.execute(stmt).scalar_one_or_none()
        if not job:
            raise ValidationError("Import job not found or unauthorized.")
        return job

    @classmethod
    def update_mapping(
        cls,
        job_id: uuid.UUID,
        user_id: uuid.UUID,
        new_mapping: Dict[str, str],
        db: Session,
    ) -> ImportJob:
        job = cls.get_job_or_raise(job_id, user_id, db)

        if job.status == ImportJobStatus.COMMITTED.value:
            raise ValidationError("Cannot modify mapping for an already committed import.")

        plat_stmt = select(Platform).where(Platform.id == job.platform_id)
        platform = db.execute(plat_stmt).scalar_one_or_none()
        platform_name = platform.name if platform else ""

        preview = job.preview_data or {}
        raw_rows = preview.get("raw_rows", [])

        # Re-generate preview with new mapping
        preview_payload = PreviewService.generate_preview(
            user_id=user_id,
            platform_id=job.platform_id,
            platform_name=platform_name,
            import_type=job.import_type,
            raw_rows=raw_rows,
            column_mapping=new_mapping,
            db=db,
        )

        job.column_mapping = new_mapping
        job.status = preview_payload["status"]
        job.valid_row_count = preview_payload["valid_row_count"]
        job.warning_count = preview_payload["warning_count"]
        job.error_count = preview_payload["error_count"]
        job.new_count = preview_payload["new_count"]
        job.duplicate_count = preview_payload["duplicate_count"]
        job.possible_duplicate_count = preview_payload["possible_duplicate_count"]
        job.preview_data = {
            **preview,
            **preview_payload,
        }
        job.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(job)
        return job

    @classmethod
    def list_user_imports(
        cls, user_id: uuid.UUID, db: Session
    ) -> List[ImportJob]:
        stmt = (
            select(ImportJob)
            .where(ImportJob.user_id == user_id)
            .order_by(desc(ImportJob.created_at))
            .limit(50)
        )
        return list(db.execute(stmt).scalars().all())

    @classmethod
    def delete_job(
        cls, job_id: uuid.UUID, user_id: uuid.UUID, db: Session
    ) -> None:
        job = cls.get_job_or_raise(job_id, user_id, db)
        if job.status == ImportJobStatus.COMMITTED.value:
            raise ValidationError("Cannot delete a committed import job from here.")
        db.delete(job)
        db.commit()
