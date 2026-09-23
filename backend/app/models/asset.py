import uuid
from datetime import datetime, date
import enum
from sqlalchemy import String, Float, DateTime, Date, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, GUID, JSONType


class AssetType(str, enum.Enum):
    STOCKS = "STOCKS"
    ETFS = "ETFS"
    MUTUAL_FUNDS = "MUTUAL_FUNDS"
    FIXED_DEPOSITS = "FIXED_DEPOSITS"
    RECURRING_DEPOSITS = "RECURRING_DEPOSITS"
    P2P_LOANS = "P2P_LOANS"
    DIGITAL_GOLD = "DIGITAL_GOLD"
    DIGITAL_SILVER = "DIGITAL_SILVER"
    CRYPTO = "CRYPTO"
    BONDS = "BONDS"
    SGB = "SGB"
    NPS = "NPS"
    EPF = "EPF"
    PPF = "PPF"
    PHYSICAL_GOLD = "PHYSICAL_GOLD"
    PHYSICAL_SILVER = "PHYSICAL_SILVER"
    REAL_ESTATE = "REAL_ESTATE"
    CASH = "CASH"
    OTHER = "OTHER"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    account_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    platform_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)  # ISIN / Folio / Contract / Address
    quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    average_buy_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    invested_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_valued_at: Mapped[datetime | None] = mapped_column(DateTime, default=datetime.utcnow, nullable=True)
    data_source: Mapped[str] = mapped_column(String(50), default="MANUAL", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSONType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="assets")
    account = relationship("Account", back_populates="assets")
    platform = relationship("Platform", back_populates="assets")
    transactions = relationship("Transaction", back_populates="asset", cascade="all, delete-orphan")
