"""Secure local transaction persistence for offline-first flow."""

from __future__ import annotations

import json
import sqlite3
import uuid
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.audit.chain import append_audit_event
from src.auth.service import derive_session_key
from src.crypto.service import (
    canonical_json,
    decrypt_payload,
    derive_crypto_keys,
    encrypt_payload,
    sign_payload,
    verify_signature,
)
from src.database.init_db import DB_PATH, init_db
from src.fraud.engine import decide_intervention, score_transaction


@dataclass(frozen=True)
class StoredTransaction:
    tx_id: str
    outbox_id: str
    status: str
    sync_state: str
    signature: str
    risk_score: int
    risk_level: str
    reason_codes: list[str]
    action_decision: str
    intervention_title: str
    intervention_guidance: list[str]


def create_secure_transaction(
    user_id: str,
    pin: str,
    amount: float,
    recipient: str,
    db_path: Path = DB_PATH,
    risk_score_override: int | None = None,
    risk_level_override: str | None = None,
    timestamp: datetime | None = None,
) -> StoredTransaction:
    """Authenticate user, encrypt transaction fields, sign record, and enqueue for sync."""
    if amount <= 0:
        raise ValueError("Amount must be greater than zero")
    if not recipient.strip():
        raise ValueError("Recipient must not be empty")

    init_db(db_path)
    session_key = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    enc_key, sig_key = derive_crypto_keys(session_key)

    tx_id = str(uuid.uuid4())
    outbox_id = str(uuid.uuid4())
    tx_time = (timestamp or datetime.now(UTC)).isoformat()
    status = "PENDING"
    sync_state = "PENDING"

    history = _load_user_history(user_id=user_id, enc_key=enc_key, db_path=db_path)
    recent_failed_attempts = _load_failed_attempts(user_id=user_id, db_path=db_path)
    risk = score_transaction(
        transaction={
            "amount": amount,
            "recipient": recipient.strip(),
            "timestamp": tx_time,
        },
        history=history,
        recent_failed_attempts=recent_failed_attempts,
    )
    risk_score = risk_score_override if risk_score_override is not None else risk["risk_score"]
    risk_level = risk_level_override if risk_level_override is not None else risk["risk_level"]
    reason_codes = risk["reason_codes"]
    intervention = decide_intervention(risk_score=risk_score, risk_level=risk_level, reason_codes=reason_codes)
    action_decision = intervention["action"]
    intervention_title = intervention["title"]
    intervention_guidance = intervention["guidance"]

    if action_decision == "HOLD":
        status = "HOLD_FOR_REVIEW"
        sync_state = "HOLD"
    elif action_decision == "BLOCK":
        status = "BLOCKED_LOCAL"
        sync_state = "BLOCKED"

    amount_payload = encrypt_payload(f"{amount:.2f}", enc_key)
    recipient_payload = encrypt_payload(recipient.strip(), enc_key)
    amount_enc = canonical_json(amount_payload)
    recipient_enc = canonical_json(recipient_payload)

    signable = {
        "tx_id": tx_id,
        "user_id": user_id,
        "amount_enc": amount_enc,
        "recipient_enc": recipient_enc,
        "timestamp": tx_time,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "status": status,
    }
    signature = sign_payload(canonical_json(signable), sig_key)

    outbox_packet = {
        "tx_id": tx_id,
        "user_id": user_id,
        "timestamp": tx_time,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason_codes": reason_codes,
        "amount_enc": amount_enc,
        "recipient_enc": recipient_enc,
        "signature": signature,
    }
    outbox_payload = encrypt_payload(canonical_json(outbox_packet), enc_key)
    idempotency_key = hashlib.sha256(tx_id.encode("utf-8")).hexdigest()

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (
                tx_id, user_id, amount_enc, recipient_enc, timestamp,
                risk_score, risk_level, reason_codes, action_decision, intervention_data, status, signature, nonce
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                user_id,
                amount_enc,
                recipient_enc,
                tx_time,
                risk_score,
                risk_level,
                canonical_json({"reason_codes": reason_codes}),
                action_decision,
                canonical_json(
                    {"title": intervention_title, "guidance": intervention_guidance}
                ),
                status,
                signature,
                amount_payload["nonce"],
            ),
        )
        if action_decision != "BLOCK":
            cursor.execute(
                """
                INSERT INTO outbox (
                    outbox_id, tx_id, idempotency_key, payload_enc, retry_count, next_retry_at, last_error, sync_state
                ) VALUES (?, ?, ?, ?, 0, NULL, NULL, ?)
                """,
                (outbox_id, tx_id, idempotency_key, canonical_json(outbox_payload), sync_state),
            )
        conn.commit()

    append_audit_event(
        event_type="TRANSACTION_CREATED",
        event_data_enc=canonical_json(
            {
                "tx_id": tx_id,
                "user_id": user_id,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "status": status,
            }
        ),
        db_path=db_path,
    )

    return StoredTransaction(
        tx_id=tx_id,
        outbox_id=outbox_id,
        status=status,
        sync_state=sync_state,
        signature=signature,
        risk_score=risk_score,
        risk_level=risk_level,
        reason_codes=reason_codes,
        action_decision=action_decision,
        intervention_title=intervention_title,
        intervention_guidance=intervention_guidance,
    )


def read_secure_transaction(
    tx_id: str,
    user_id: str,
    pin: str,
    db_path: Path = DB_PATH,
) -> dict:
    """Read, verify integrity, and decrypt one transaction."""
    init_db(db_path)
    session_key = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    enc_key, sig_key = derive_crypto_keys(session_key)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT tx_id, user_id, amount_enc, recipient_enc, timestamp,
                   risk_score, risk_level, reason_codes, action_decision, intervention_data, status, signature
            FROM transactions
            WHERE tx_id = ? AND user_id = ?
            """,
            (tx_id, user_id),
        )
        row = cursor.fetchone()

    if row is None:
        raise ValueError("Transaction not found")

    (
        row_tx_id,
        row_user_id,
        amount_enc,
        recipient_enc,
        tx_time,
        risk_score,
        risk_level,
        reason_codes_raw,
        action_decision,
        intervention_raw,
        status,
        signature,
    ) = row

    signable = {
        "tx_id": row_tx_id,
        "user_id": row_user_id,
        "amount_enc": amount_enc,
        "recipient_enc": recipient_enc,
        "timestamp": tx_time,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "status": status,
    }
    if not verify_signature(canonical_json(signable), signature, sig_key):
        raise ValueError("Transaction integrity check failed")

    amount = decrypt_payload(json.loads(amount_enc), enc_key)
    recipient = decrypt_payload(json.loads(recipient_enc), enc_key)

    return {
        "tx_id": row_tx_id,
        "user_id": row_user_id,
        "amount": amount,
        "recipient": recipient,
        "timestamp": tx_time,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "reason_codes": _parse_reason_codes(reason_codes_raw),
        "action_decision": action_decision or "ALLOW",
        "intervention": _parse_intervention(intervention_raw),
        "status": status,
    }


def list_secure_transactions(
    user_id: str,
    pin: str,
    db_path: Path = DB_PATH,
    limit: int = 20,
) -> list[dict]:
    """List and decrypt recent user transactions with integrity checks."""
    init_db(db_path)
    session_key = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    enc_key, sig_key = derive_crypto_keys(session_key)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT tx_id, amount_enc, recipient_enc, timestamp, risk_score, risk_level, status, signature
                   ,reason_codes, action_decision, intervention_data
            FROM transactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        rows = cursor.fetchall()

    transactions: list[dict] = []
    for row in rows:
        (
            tx_id,
            amount_enc,
            recipient_enc,
            tx_time,
            risk_score,
            risk_level,
            status,
            signature,
            reason_codes_raw,
            action_decision,
            intervention_raw,
        ) = row
        signable = {
            "tx_id": tx_id,
            "user_id": user_id,
            "amount_enc": amount_enc,
            "recipient_enc": recipient_enc,
            "timestamp": tx_time,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "status": status,
        }
        integrity_ok = verify_signature(canonical_json(signable), signature, sig_key)
        if not integrity_ok:
            transactions.append(
                {
                    "tx_id": tx_id,
                    "timestamp": tx_time,
                    "status": "REJECTED_INTEGRITY_FAIL",
                    "risk_score": risk_score,
                    "risk_level": risk_level,
                    "reason_codes": _parse_reason_codes(reason_codes_raw),
                    "action_decision": action_decision or "ALLOW",
                    "intervention": _parse_intervention(intervention_raw),
                    "amount": None,
                    "recipient": None,
                }
            )
            continue

        amount = decrypt_payload(json.loads(amount_enc), enc_key)
        recipient = decrypt_payload(json.loads(recipient_enc), enc_key)
        transactions.append(
            {
                "tx_id": tx_id,
                "timestamp": tx_time,
                "status": status,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "reason_codes": _parse_reason_codes(reason_codes_raw),
                "action_decision": action_decision or "ALLOW",
                "intervention": _parse_intervention(intervention_raw),
                "amount": amount,
                "recipient": recipient,
            }
        )

    return transactions


def _load_user_history(user_id: str, enc_key: bytes, db_path: Path) -> list[dict]:
    """Load and decrypt recent transaction metadata for local fraud scoring."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT amount_enc, recipient_enc, timestamp
            FROM transactions
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 20
            """,
            (user_id,),
        )
        rows = cursor.fetchall()

    history: list[dict] = []
    for amount_enc, recipient_enc, tx_time in rows:
        try:
            amount = decrypt_payload(json.loads(amount_enc), enc_key)
            recipient = decrypt_payload(json.loads(recipient_enc), enc_key)
            history.append(
                {
                    "amount": amount,
                    "recipient": recipient,
                    "timestamp": tx_time,
                }
            )
        except Exception:
            continue
    return history


def _load_failed_attempts(user_id: str, db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT failed_attempts FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    return int(row[0]) if row else 0


def get_dashboard_stats(db_path: Path = DB_PATH) -> dict:
    """Return aggregate counters for UI dashboard cards."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = int(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM transactions")
        tx_count = int(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'PENDING'")
        pending_count = int(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM transactions WHERE status = 'SYNCED'")
        synced_count = int(cursor.fetchone()[0])

        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE risk_level = 'HIGH' OR risk_score >= 70"
        )
        high_risk_count = int(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM audit_log")
        audit_events = int(cursor.fetchone()[0])

    return {
        "user_count": user_count,
        "tx_count": tx_count,
        "pending_count": pending_count,
        "synced_count": synced_count,
        "high_risk_count": high_risk_count,
        "audit_events": audit_events,
    }


def _parse_reason_codes(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            codes = payload.get("reason_codes", [])
            if isinstance(codes, list):
                return [str(x) for x in codes]
    except Exception:
        return []
    return []


def _parse_intervention(raw: str | None) -> dict:
    if not raw:
        return {"title": "", "guidance": []}
    try:
        payload = json.loads(raw)
        title = str(payload.get("title", ""))
        guidance = payload.get("guidance", [])
        if not isinstance(guidance, list):
            guidance = []
        return {"title": title, "guidance": [str(x) for x in guidance]}
    except Exception:
        return {"title": "", "guidance": []}


def release_held_transaction(
    tx_id: str,
    user_id: str,
    pin: str,
    db_path: Path = DB_PATH,
) -> bool:
    """Release one held transaction after successful user authentication."""
    init_db(db_path)
    session_key = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    _, sig_key = derive_crypto_keys(session_key)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT amount_enc, recipient_enc, timestamp, risk_score, risk_level, status
            FROM transactions WHERE tx_id = ? AND user_id = ?
            """,
            (tx_id, user_id),
        )
        row = cursor.fetchone()
        if row is None:
            return False
        amount_enc, recipient_enc, tx_time, risk_score, risk_level, status = row
        if status != "HOLD_FOR_REVIEW":
            return False

        new_status = "PENDING"
        signable = {
            "tx_id": tx_id,
            "user_id": user_id,
            "amount_enc": amount_enc,
            "recipient_enc": recipient_enc,
            "timestamp": tx_time,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "status": new_status,
        }
        new_signature = sign_payload(canonical_json(signable), sig_key)

        cursor.execute(
            "UPDATE transactions SET status = ?, signature = ? WHERE tx_id = ?",
            (new_status, new_signature, tx_id),
        )
        cursor.execute(
            "UPDATE outbox SET sync_state = 'PENDING' WHERE tx_id = ?",
            (tx_id,),
        )
        conn.commit()

    append_audit_event(
        event_type="TRANSACTION_RELEASED",
        event_data_enc=canonical_json({"tx_id": tx_id, "user_id": user_id}),
        db_path=db_path,
    )
    return True
