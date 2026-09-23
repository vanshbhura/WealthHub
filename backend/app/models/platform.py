import uuid
from datetime import datetime
import enum
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, GUID


class PlatformCategory(str, enum.Enum):
    BANK = "BANK"
    BROKER = "BROKER"
    MUTUAL_FUND = "MUTUAL_FUND"
    P2P = "P2P"
    DIGITAL_GOLD = "DIGITAL_GOLD"
    DIGITAL_SILVER = "DIGITAL_SILVER"
    CRYPTO = "CRYPTO"
    INSURANCE = "INSURANCE"
    RETIREMENT = "RETIREMENT"
    AGGREGATOR = "AGGREGATOR"
    OTHER = "OTHER"


class IntegrationType(str, enum.Enum):
    ACCOUNT_AGGREGATOR = "ACCOUNT_AGGREGATOR"
    DIRECT_API = "DIRECT_API"
    OAUTH = "OAUTH"
    OFFICIAL_API = "OFFICIAL_API"
    PROVIDER_API = "PROVIDER_API"
    STATEMENT_IMPORT = "STATEMENT_IMPORT"
    IMPORT = "IMPORT"
    MANUAL = "MANUAL"
    COMING_SOON = "COMING_SOON"


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    integration_type: Mapped[str] = mapped_column(String(50), default="STATEMENT_IMPORT", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    connections = relationship("Connection", back_populates="platform")
    connectors = relationship("PlatformConnector", back_populates="platform", cascade="all, delete-orphan")
    accounts = relationship("Account", back_populates="platform")
    assets = relationship("Asset", back_populates="platform")
