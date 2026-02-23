"""Tamper-evident local audit chain utilities."""

from __future__ import annotations

import hashlib
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.database.init_db import DB_PATH, init_db


@dataclass(frozen=True)
class AuditEntry:
    log_id: str
    event_type: str
    prev_hash: str | None
    curr_hash: str
    created_at: str


@dataclass(frozen=True)
class AuditVerificationResult:
    is_valid: bool
    checked_entries: int
    error: str | None = None


def append_audit_event(
    event_type: str,
    event_data_enc: str,
    db_path: Path = DB_PATH,
    created_at: datetime | None = None,
    conn: sqlite3.Connection | None = None,
) -> AuditEntry:
    """Append one hash-linked audit event."""
    init_db(db_path)
    event_time = (created_at or datetime.now(UTC)).isoformat()
    log_id = str(uuid.uuid4())

    managed_conn = conn is None
    active_conn = conn or sqlite3.connect(db_path)
    cursor = active_conn.cursor()
    cursor.execute(
        "SELECT curr_hash FROM audit_log ORDER BY created_at DESC, rowid DESC LIMIT 1"
    )
    row = cursor.fetchone()
    prev_hash = row[0] if row else None

    curr_hash = _compute_hash(
        log_id=log_id,
        event_type=event_type,
        event_data_enc=event_data_enc,
        prev_hash=prev_hash,
        created_at=event_time,
    )

    cursor.execute(
        """
        INSERT INTO audit_log (log_id, event_type, event_data_enc, prev_hash, curr_hash, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (log_id, event_type, event_data_enc, prev_hash, curr_hash, event_time),
    )
    if managed_conn:
        active_conn.commit()
        active_conn.close()

    return AuditEntry(
        log_id=log_id,
        event_type=event_type,
        prev_hash=prev_hash,
        curr_hash=curr_hash,
        created_at=event_time,
    )


def verify_audit_chain(db_path: Path = DB_PATH) -> AuditVerificationResult:
    """Verify chain linkage and hashes for all audit entries."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT log_id, event_type, event_data_enc, prev_hash, curr_hash, created_at
            FROM audit_log
            ORDER BY created_at ASC, rowid ASC
            """
        )
        rows = cursor.fetchall()

    previous_hash = None
    checked = 0
    for log_id, event_type, event_data_enc, prev_hash, curr_hash, created_at in rows:
        if prev_hash != previous_hash:
            return AuditVerificationResult(
                is_valid=False,
                checked_entries=checked,
                error=f"Broken prev_hash link at log_id={log_id}",
            )

        expected_hash = _compute_hash(
            log_id=log_id,
            event_type=event_type,
            event_data_enc=event_data_enc,
            prev_hash=prev_hash,
            created_at=created_at,
        )
        if curr_hash != expected_hash:
            return AuditVerificationResult(
                is_valid=False,
                checked_entries=checked,
                error=f"Hash mismatch at log_id={log_id}",
            )

        previous_hash = curr_hash
        checked += 1

    return AuditVerificationResult(is_valid=True, checked_entries=checked)


def _compute_hash(
    log_id: str,
    event_type: str,
    event_data_enc: str,
    prev_hash: str | None,
    created_at: str,
) -> str:
    payload = "|".join(
        [log_id, event_type, event_data_enc, prev_hash or "", created_at]
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
