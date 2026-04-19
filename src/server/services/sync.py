from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.server.models.sync import SyncLog, SyncQueue
from src.server.models.transaction import Transaction


def push_outbox(db: Session, *, user_id: str, items: list[dict]) -> list[dict]:
    """Accept offline outbox items (idempotent) and queue for processing.

    Conflict resolution policy (server authority):
    - If server already has tx_id: treat as duplicate and return server status.
    - If idempotency key already logged: duplicate.
    - Otherwise: enqueue payload for later validation/processing.
    """
    results: list[dict] = []
    for item in items:
        tx_id = str(item.get("tx_id", ""))
        idem = str(item.get("idempotency_key", ""))
        payload_enc = str(item.get("payload_enc", ""))
        if not tx_id or not idem or not payload_enc:
            results.append(
                {
                    "tx_id": tx_id,
                    "idempotency_key": idem,
                    "result": "rejected",
                    "detail": "missing_fields",
                    "server_status": "REJECTED",
                }
            )
            continue

        existing_log = db.execute(
            select(SyncLog).where(SyncLog.user_id == user_id, SyncLog.idempotency_key == idem)
        ).scalar_one_or_none()
        if existing_log:
            results.append(
                {
                    "tx_id": tx_id,
                    "idempotency_key": idem,
                    "result": "duplicate",
                    "detail": "",
                    "server_status": "SYNCED",
                }
            )
            continue

        tx = db.get(Transaction, tx_id)
        if tx is None:
            db.add(
                SyncQueue(
                    queue_id=uuid.uuid4().hex,
                    user_id=user_id,
                    tx_id=tx_id,
                    idempotency_key=idem,
                    payload_enc=payload_enc,
                    state="PENDING",
                    retry_count=0,
                    last_error="",
                )
            )
            db.add(
                SyncLog(
                    log_id=uuid.uuid4().hex,
                    user_id=user_id,
                    tx_id=tx_id,
                    idempotency_key=idem,
                    result="synced",
                    detail="queued_for_processing",
                )
            )
            db.commit()
            results.append(
                {
                    "tx_id": tx_id,
                    "idempotency_key": idem,
                    "result": "synced",
                    "detail": "queued_for_processing",
                    "server_status": "SYNCED",
                }
            )
            continue

        db.add(
            SyncLog(
                log_id=uuid.uuid4().hex,
                user_id=user_id,
                tx_id=tx_id,
                idempotency_key=idem,
                result="duplicate",
                detail="server_authority",
            )
        )
        db.commit()
        results.append(
            {
                "tx_id": tx_id,
                "idempotency_key": idem,
                "result": "duplicate",
                "detail": "server_authority",
                "server_status": tx.status,
            }
        )
    return results


def server_time() -> str:
    return datetime.now(UTC).isoformat()

