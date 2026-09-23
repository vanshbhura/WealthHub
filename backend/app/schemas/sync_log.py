import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SyncLogResponse(BaseModel):
    id: uuid.UUID
    connection_id: uuid.UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    records_processed: int
    records_created: int
    records_updated: int
    error_code: Optional[str] = None
    safe_error_message: Optional[str] = None

    class Config:
        from_attributes = True
