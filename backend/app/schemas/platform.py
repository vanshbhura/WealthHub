import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class PlatformResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    category: str
    logo_url: Optional[str] = None
    description: Optional[str] = None
    integration_type: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
