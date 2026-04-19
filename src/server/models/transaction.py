from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.server.db.base import Base


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_transactions_user_idem"),
    )

    tx_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    device_id: Mapped[str] = mapped_column(String(128), index=True, default="")

    # Amount is stored as numeric for reporting/limits; recipient is encrypted.
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    recipient_enc: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0, index=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, default="LOW", index=True)
    reason_codes: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", index=True)

    signature: Mapped[str] = mapped_column(Text, nullable=False, default="")
    idempotency_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    user = relationship("User", back_populates="transactions")
