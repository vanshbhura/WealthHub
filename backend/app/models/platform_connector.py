import uuid
from datetime import datetime
import enum
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, GUID, JSONType


class ConnectorType(str, enum.Enum):
    DIRECT_API = "DIRECT_API"
    ACCOUNT_AGGREGATOR = "ACCOUNT_AGGREGATOR"
    PROVIDER_API = "PROVIDER_API"
    IMPORT = "IMPORT"
    MANUAL = "MANUAL"


class ConnectorStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    COMING_SOON = "COMING_SOON"
    PLANNED = "PLANNED"
    SANDBOX = "SANDBOX"


class PlatformConnector(Base):
    __tablename__ = "platform_connectors"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    platform_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connector_type: Mapped[str] = mapped_column(String(50), nullable=False)
    connector_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="COMING_SOON", nullable=False)
    capabilities: Mapped[list] = mapped_column(JSONType, default=list, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    platform = relationship("Platform", back_populates="connectors")
