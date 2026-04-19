from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.server.core.security import encrypt_field
from src.server.models.device import Device
from src.server.models.transaction import Transaction
from src.server.services.fraud import behavioral_profile, dynamic_risk_score, log_fraud


def create_transaction(
    db: Session,
    *,
    user_id: str,
    amount: float,
    recipient: str,
    device_id: str,
    idempotency_key: str,
) -> Transaction:
    # Idempotency: if already exists, return it.
    existing = db.execute(
        select(Transaction).where(Transaction.user_id == user_id, Transaction.idempotency_key == idempotency_key)
    ).scalar_one_or_none()
    if existing:
        return existing

    # Recipient novelty check (very lightweight): compare encrypted recipient tokens not possible,
    # so use amount+recipient plaintext check at service boundary (recipient isn't stored plaintext).
    # For production you’d store a separate recipient hash for novelty.
    recipient_is_new = True

    device = db.get(Device, device_id) if device_id else None
    new_device = bool(device_id) and (device is None or device.user_id != user_id or device.trust_level == "untrusted")

    profile = behavioral_profile(db, user_id=user_id)
    risk_score, risk_level, reasons = dynamic_risk_score(
        amount=amount,
        recipient_is_new=recipient_is_new,
        profile=profile,
        new_device=new_device,
    )

    status = "PENDING"
    if risk_level == "HIGH" or new_device:
        status = "HOLD_FOR_REVIEW"

    tx_id = uuid.uuid4().hex
    recipient_enc = encrypt_field(recipient, aad=f"tx:{tx_id}")
    tx = Transaction(
        tx_id=tx_id,
        user_id=user_id,
        device_id=device_id or "",
        amount=float(amount),
        recipient_enc=recipient_enc,
        risk_score=risk_score,
        risk_level=risk_level,
        reason_codes=json.dumps(reasons),
        status=status,
        idempotency_key=idempotency_key,
        signature="",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    log_fraud(
        db,
        log_id=uuid.uuid4().hex,
        tx_id=tx.tx_id,
        user_id=user_id,
        risk_score=risk_score,
        risk_level=risk_level,
        reasons=reasons,
    )
    return tx

