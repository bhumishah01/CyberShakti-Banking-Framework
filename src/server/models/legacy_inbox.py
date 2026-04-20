from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.server.db.base import Base


class LegacySyncInbox(Base):
    """Stores offline-first sync payloads sent from low-end devices.

    This table is intentionally "raw": it stores encrypted payload blobs (`payload_enc`)
    plus idempotency metadata, so the server can acknowledge receipt even if it cannot
    fully parse/decrypt the payload at that moment.
    """

    __tablename__ = "legacy_sync_inbox"
    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="uq_legacyinbox_user_idem"),
    )

    inbox_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    tx_id: Mapped[str] = mapped_column(String(64), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), index=True)
    payload_enc: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

