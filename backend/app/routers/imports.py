import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.schemas.import_job import (
    ImportJobResponse,
    ImportPreviewResponse,
    UpdateMappingRequest,
    CommitImportResponse,
)
from app.imports.services.import_service import ImportService
from app.imports.services.commit_service import CommitService
from app.imports.mappers.mapping_profiles import NORMALIZED_FIELDS
from app.imports.exceptions import ImportError as CoreImportError

router = APIRouter(prefix="/api/imports", tags=["Statement Import"])


@router.post("", response_model=ImportPreviewResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_parse_statement(
    file: UploadFile = File(...),
    platform_id: uuid.UUID = Form(...),
    import_type: str = Form("BROKER"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload and parse financial statement (CSV, XLSX, or PDF).
    Performs security checks, auto-maps columns, validates rows, and returns a preview.
    Zero production financial tables are modified during this stage.
    """
    try:
        file_bytes = await file.read()
        job = ImportService.create_import_job(
            user_id=current_user.id,
            platform_id=platform_id,
            import_type=import_type.upper(),
            file_bytes=file_bytes,
            filename=file.filename or "statement",
            db=db,
        )

        preview = job.preview_data or {}
        return ImportPreviewResponse(
            id=job.id,
            status=job.status,
            file_name=job.file_name,
            platform_id=job.platform_id,
            import_type=job.import_type,
            row_count=job.row_count,
            valid_row_count=job.valid_row_count,
            warning_count=job.warning_count,
            error_count=job.error_count,
            new_count=job.new_count,
            duplicate_count=job.duplicate_count,
            possible_duplicate_count=job.possible_duplicate_count,
            headers=preview.get("headers", []),
            column_mapping=job.column_mapping,
            available_fields=NORMALIZED_FIELDS,
            accounts_detected=preview.get("accounts_detected", []),
            assets_detected=preview.get("assets_detected", []),
            issues=preview.get("issues", []),
            rows=preview.get("rows", []),
        )
    except CoreImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_IMPORT_ERROR", "message": f"Failed to process statement: {str(e)}"},
        )


@router.get("", response_model=List[ImportJobResponse])
def list_import_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lists the authenticated user's statement import history."""
    jobs = ImportService.list_user_imports(user_id=current_user.id, db=db)
    return [ImportJobResponse.model_validate(j) for j in jobs]


@router.get("/{import_id}", response_model=ImportJobResponse)
def get_import_status(
    import_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve import job status and metadata."""
    try:
        job = ImportService.get_job_or_raise(job_id=import_id, user_id=current_user.id, db=db)
        return ImportJobResponse.model_validate(job)
    except CoreImportError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        )


@router.get("/{import_id}/preview", response_model=ImportPreviewResponse)
def get_import_preview(
    import_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve full preview rows, column mappings, and validation messages."""
    try:
        job = ImportService.get_job_or_raise(job_id=import_id, user_id=current_user.id, db=db)
        preview = job.preview_data or {}
        return ImportPreviewResponse(
            id=job.id,
            status=job.status,
            file_name=job.file_name,
            platform_id=job.platform_id,
            import_type=job.import_type,
            row_count=job.row_count,
            valid_row_count=job.valid_row_count,
            warning_count=job.warning_count,
            error_count=job.error_count,
            new_count=job.new_count,
            duplicate_count=job.duplicate_count,
            possible_duplicate_count=job.possible_duplicate_count,
            headers=preview.get("headers", []),
            column_mapping=job.column_mapping,
            available_fields=NORMALIZED_FIELDS,
            accounts_detected=preview.get("accounts_detected", []),
            assets_detected=preview.get("assets_detected", []),
            issues=preview.get("issues", []),
            rows=preview.get("rows", []),
        )
    except CoreImportError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": e.code, "message": e.message},
        )


@router.post("/{import_id}/map", response_model=ImportPreviewResponse)
def update_column_mapping(
    import_id: uuid.UUID,
    payload: UpdateMappingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Updates column mapping and re-runs statement validation and preview."""
    try:
        job = ImportService.update_mapping(
            job_id=import_id,
            user_id=current_user.id,
            new_mapping=payload.column_mapping,
            db=db,
        )
        preview = job.preview_data or {}
        return ImportPreviewResponse(
            id=job.id,
            status=job.status,
            file_name=job.file_name,
            platform_id=job.platform_id,
            import_type=job.import_type,
            row_count=job.row_count,
            valid_row_count=job.valid_row_count,
            warning_count=job.warning_count,
            error_count=job.error_count,
            new_count=job.new_count,
            duplicate_count=job.duplicate_count,
            possible_duplicate_count=job.possible_duplicate_count,
            headers=preview.get("headers", []),
            column_mapping=job.column_mapping,
            available_fields=NORMALIZED_FIELDS,
            accounts_detected=preview.get("accounts_detected", []),
            assets_detected=preview.get("assets_detected", []),
            issues=preview.get("issues", []),
            rows=preview.get("rows", []),
        )
    except CoreImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )


@router.post("/{import_id}/validate", response_model=ImportPreviewResponse)
def revalidate_statement(
    import_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Re-executes statement validation against current mappings."""
    try:
        job = ImportService.get_job_or_raise(job_id=import_id, user_id=current_user.id, db=db)
        return get_import_preview(import_id=job.id, current_user=current_user, db=db)
    except CoreImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )


@router.post("/{import_id}/commit", response_model=CommitImportResponse)
def commit_statement(
    import_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Atomically commits the validated import job.
    Creates accounts, assets, transactions, updates connection status,
    recalculates total wealth, and captures a portfolio snapshot.
    """
    try:
        result = CommitService.commit_import_job(
            import_job_id=import_id,
            user_id=current_user.id,
            db=db,
        )
        return CommitImportResponse(**result)
    except CoreImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )


@router.delete("/{import_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_import(
    import_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancels/deletes an uncommitted import job."""
    try:
        ImportService.delete_job(job_id=import_id, user_id=current_user.id, db=db)
    except CoreImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": e.code, "message": e.message},
        )
