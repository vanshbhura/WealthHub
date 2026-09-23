import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base, GUID


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("connections.id", ondelete="SET NULL"), nullable=True, index=True)
    platform_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False, index=True)
    account_name: Mapped[str] = mapped_column(String(150), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., DEMAT, SAVINGS, P2P_WALLET
    masked_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g., ****4102
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    current_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    invested_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="accounts")
    connection = relationship("Connection", back_populates="accounts")
    platform = relationship("Platform", back_populates="accounts")
    assets = relationship("Asset", back_populates="account", cascade="all, delete-orphan")
