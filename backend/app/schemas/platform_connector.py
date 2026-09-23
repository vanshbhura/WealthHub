import uuid
from typing import List, Optional
from pydantic import BaseModel


class PlatformConnectorResponse(BaseModel):
    id: Optional[uuid.UUID] = None
    platform_id: Optional[uuid.UUID] = None
    connector_type: str
    connector_key: str
    name: Optional[str] = None
    status: str  # AVAILABLE, COMING_SOON, PLANNED
    capabilities: List[str] = []
    is_enabled: bool = False
    requirements: Optional[str] = None

    class Config:
        from_attributes = True
