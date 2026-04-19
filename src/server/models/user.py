from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.server.db.base import Base


class UserRole(str, Enum):
    customer = "customer"
    bank_officer = "bank_officer"
    agent = "agent"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    devices = relationship("Device", back_populates="user", cascade="all,delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all,delete-orphan")

