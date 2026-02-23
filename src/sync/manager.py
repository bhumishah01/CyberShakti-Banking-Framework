"""Outbox sync manager with retry, backoff, and idempotency support."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from src.audit.chain import append_audit_event
from src.crypto.service import canonical_json
from src.database.init_db import DB_PATH, init_db

MAX_BACKOFF_MINUTES = 60


@dataclass(frozen=True)
class SyncSummary:
    processed: int
    synced: int
    duplicates: int
    retried: int


def sync_outbox(
    db_path: Path = DB_PATH,
    sender: Callable[[dict], dict] | None = None,
    now: datetime | None = None,
    batch_size: int = 20,
) -> SyncSummary:
    """Sync due outbox records and update local states."""
    if sender is None:
        raise ValueError("A sender callback is required for sync_outbox")

    init_db(db_path)
    current_time = now or datetime.now(UTC)
    processed = 0
    synced = 0
    duplicates = 0
    retried = 0

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT outbox_id, tx_id, idempotency_key, payload_enc, retry_count
            FROM outbox
            WHERE sync_state IN ('PENDING', 'RETRYING')
              AND (next_retry_at IS NULL OR next_retry_at <= ?)
            ORDER BY rowid ASC
            LIMIT ?
            """,
            (current_time.isoformat(), batch_size),
        )
        rows = cursor.fetchall()

        for outbox_id, tx_id, idempotency_key, payload_enc, retry_count in rows:
            processed += 1
            idempotency = idempotency_key or _derive_idempotency_key(tx_id)

            try:
                ack = sender(
                    {
                        "tx_id": tx_id,
                        "idempotency_key": idempotency,
                        "payload_enc": payload_enc,
                    }
                )
                status = str(ack.get("status", "synced")).lower()
                if status not in {"synced", "duplicate"}:
                    raise ValueError(f"Unexpected sync status: {status}")

                if status == "synced":
                    outbox_state = "SYNCED"
                    tx_state = "SYNCED"
                    synced += 1
                else:
                    outbox_state = "SYNCED_DUPLICATE_ACK"
                    tx_state = "SYNCED_DUPLICATE_ACK"
                    duplicates += 1

                cursor.execute(
                    """
                    UPDATE outbox
                    SET idempotency_key = ?, sync_state = ?, next_retry_at = NULL, last_error = NULL
                    WHERE outbox_id = ?
                    """,
                    (idempotency, outbox_state, outbox_id),
                )
                cursor.execute(
                    "UPDATE transactions SET status = ? WHERE tx_id = ?",
                    (tx_state, tx_id),
                )
                append_audit_event(
                    event_type="SYNC_RESULT",
                    event_data_enc=canonical_json(
                        {
                            "tx_id": tx_id,
                            "outbox_id": outbox_id,
                            "result": outbox_state,
                            "retry_count": retry_count,
                        }
                    ),
                    db_path=db_path,
                    conn=conn,
                )
            except Exception as exc:
                retried += 1
                next_retry_count = int(retry_count) + 1
                next_retry_at = (
                    current_time
                    + timedelta(minutes=min(2**next_retry_count, MAX_BACKOFF_MINUTES))
                ).isoformat()
                cursor.execute(
                    """
                    UPDATE outbox
                    SET idempotency_key = ?, retry_count = ?, next_retry_at = ?, last_error = ?, sync_state = 'RETRYING'
                    WHERE outbox_id = ?
                    """,
                    (idempotency, next_retry_count, next_retry_at, str(exc), outbox_id),
                )
                cursor.execute(
                    "UPDATE transactions SET status = 'RETRYING_SYNC' WHERE tx_id = ?",
                    (tx_id,),
                )
                append_audit_event(
                    event_type="SYNC_RETRY_SCHEDULED",
                    event_data_enc=canonical_json(
                        {
                            "tx_id": tx_id,
                            "outbox_id": outbox_id,
                            "retry_count": next_retry_count,
                            "next_retry_at": next_retry_at,
                            "error": str(exc),
                        }
                    ),
                    db_path=db_path,
                    conn=conn,
                )

        conn.commit()

    return SyncSummary(
        processed=processed,
        synced=synced,
        duplicates=duplicates,
        retried=retried,
    )


def _derive_idempotency_key(tx_id: str) -> str:
    return hashlib.sha256(tx_id.encode("utf-8")).hexdigest()
