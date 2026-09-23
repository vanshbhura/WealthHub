import uuid
from datetime import datetime
import enum
from sqlalchemy import String, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, GUID, JSONType


class ConnectionStatus(str, enum.Enum):
    CONNECTED = "CONNECTED"
    CONNECTING = "CONNECTING"
    SYNCING = "SYNCING"
    SYNCED = "SYNCED"
    SYNC_FAILED = "SYNC_FAILED"
    DISCONNECTED = "DISCONNECTED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    TOKEN_EXPIRED = "AUTH_REQUIRED"
    ERROR = "ERROR"
    IMPORT_ONLY = "IMPORT_ONLY"
    MANUAL = "MANUAL"
    AVAILABLE = "AVAILABLE"
    COMING_SOON = "COMING_SOON"
    SANDBOX = "SANDBOX"


class ConnectionType(str, enum.Enum):
    DIRECT_API = "DIRECT_API"
    ACCOUNT_AGGREGATOR = "ACCOUNT_AGGREGATOR"
    PROVIDER_API = "PROVIDER_API"
    IMPORT = "IMPORT"
    MANUAL = "MANUAL"
    # Legacy aliases
    OAUTH = "DIRECT_API"
    OFFICIAL_API = "DIRECT_API"
    IMPORT_ONLY = "IMPORT"


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_type: Mapped[str] = mapped_column(String(50), default="MANUAL", nullable=False)
    connector_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="CONNECTED", nullable=False)
    external_account_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_sync_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Consent lifecycle fields (Account Aggregator & delegated auth)
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    consent_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    consent_status: Mapped[str | None] = mapped_column(String(50), nullable=True)  # PENDING, ACTIVE, REJECTED, EXPIRED, REVOKED, ERROR
    consent_created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    consent_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_consent_sync: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_data_fetch: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    provider_metadata: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="connections")
    platform = relationship("Platform", back_populates="connections")
    accounts = relationship("Account", back_populates="connection", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="connection", cascade="all, delete-orphan", order_by="SyncLog.started_at.desc()")
