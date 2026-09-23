import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    platform_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    import_type: str
    file_name: str
    file_type: str
    file_size: int
    status: str
    row_count: int
    valid_row_count: int
    warning_count: int
    error_count: int
    new_count: int
    duplicate_count: int
    possible_duplicate_count: int
    error_message: Optional[str] = None
    column_mapping: Dict[str, str]
    created_at: datetime
    updated_at: datetime
    committed_at: Optional[datetime] = None


class ImportPreviewResponse(BaseModel):
    id: uuid.UUID
    status: str
    file_name: str
    platform_id: uuid.UUID
    import_type: str
    row_count: int
    valid_row_count: int
    warning_count: int
    error_count: int
    new_count: int
    duplicate_count: int
    possible_duplicate_count: int
    headers: List[str]
    column_mapping: Dict[str, str]
    available_fields: List[Dict[str, Any]]
    accounts_detected: List[str]
    assets_detected: List[str]
    issues: List[Dict[str, Any]]
    rows: List[Dict[str, Any]]


class UpdateMappingRequest(BaseModel):
    column_mapping: Dict[str, str]


class CommitImportResponse(BaseModel):
    import_job_id: str
    platform_id: str
    platform_name: str
    status: str
    committed_transactions: int
    skipped_duplicates: int
    assets_processed: int
    records_created: int
    records_updated: int
    committed_at: str
