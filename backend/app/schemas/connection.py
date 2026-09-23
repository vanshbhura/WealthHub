import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.schemas.platform import PlatformResponse
from app.schemas.sync_log import SyncLogResponse


class ConnectionCreate(BaseModel):
    platform_id: uuid.UUID
    connection_type: str = "MANUAL"  # MANUAL, DIRECT_API, ACCOUNT_AGGREGATOR, IMPORT, etc.
    connector_key: Optional[str] = None
    external_account_reference: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None


class ConnectionTestRequest(BaseModel):
    platform_id: uuid.UUID
    connector_key: Optional[str] = "groww_direct"
    credentials: Dict[str, Any]


class ConnectionTestResponse(BaseModel):
    success: bool
    status: str
    message: str
    ucc: Optional[str] = None
    vendor_user_id: Optional[str] = None
    active_segments: List[str] = []


class ConnectionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    platform_id: uuid.UUID
    connection_type: str
    connector_key: Optional[str] = None
    status: str
    external_account_reference: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    platform: Optional[PlatformResponse] = None

    class Config:
        from_attributes = True


class ConnectionStatusResponse(BaseModel):
    id: uuid.UUID
    platform_id: uuid.UUID
    connection_type: str
    connector_key: Optional[str] = None
    status: str
    last_synced_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    last_sync_error: Optional[str] = None
    recent_logs: List[SyncLogResponse] = []
