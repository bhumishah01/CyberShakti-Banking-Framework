"""Secure local transaction persistence for offline-first flow.

This file is the core of the project:
- encrypts amount/recipient locally
- scores fraud risk
- decides allow/hold/block
- writes to outbox for later sync
"""

from __future__ import annotations

import json
import sqlite3
import uuid
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from secrets import randbelow

from src.audit.chain import append_audit_event
from src.audit.change_log import log_change
from src.auth.service import derive_session_key, get_user_auth_config, is_user_frozen
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

# === Risk approval rules ===
APPROVAL_EXPIRY_MINUTES = 15
MAX_APPROVAL_ATTEMPTS = 3


@dataclass(frozen=True)
class StoredTransaction:
    # Simple container used by UI and CLI responses
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
    approval_required: bool
    trusted_contact_hint: str
    approval_code_for_demo: str


def create_secure_transaction(
    user_id: str,
    pin: str,
    amount: float,
    recipient: str,
    db_path: Path = DB_PATH,
    risk_score_override: int | None = None,
    risk_level_override: str | None = None,
    timestamp: datetime | None = None,
    extra_reason_codes: list[str] | None = None,
    extra_risk_points: int = 0,
    force_hold: bool = False,
) -> StoredTransaction:
    """Authenticate user, encrypt transaction fields, sign record, and enqueue for sync."""
    # Basic input checks
    if amount <= 0:
        raise ValueError("Amount must be greater than zero")
    if not recipient.strip():
        raise ValueError("Recipient must not be empty")

    # Ensure local DB schema exists
    init_db(db_path)
    # Derive session key from PIN, then derive encryption + signature keys
    session_key = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    enc_key, sig_key = derive_crypto_keys(session_key)

    tx_id = str(uuid.uuid4())
    outbox_id = str(uuid.uuid4())
    tx_time = (timestamp or datetime.now(UTC)).isoformat()
    status = "PENDING"
    sync_state = "PENDING"

    # Local fraud scoring uses recent history + failed attempts (offline-first).
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
    reason_codes = list(risk["reason_codes"])
    if extra_reason_codes:
        for code in extra_reason_codes:
            if code and code not in reason_codes:
                reason_codes.append(code)
    if extra_risk_points:
        risk_score = min(100, max(0, int(risk_score) + int(extra_risk_points)))
        if risk_score >= 70:
            risk_level = "HIGH"
        elif risk_score >= 40:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
    # Decide allow/hold/block based on risk
    intervention = decide_intervention(risk_score=risk_score, risk_level=risk_level, reason_codes=reason_codes)
    action_decision = intervention["action"]
    intervention_title = intervention["title"]
    intervention_guidance = intervention["guidance"]
    approval_required = False
    approval_code_hash = None
    approval_expires_at = None
    approval_attempts = 0
    trusted_contact_hint = ""
    approval_code_for_demo = ""

    # Pull trusted-contact config for step-up approvals
    auth_config = get_user_auth_config(user_id=user_id, db_path=db_path)
    trusted_contact = str(auth_config.get("trusted_contact", "")).strip()

    # Panic freeze overrides everything
    if is_user_frozen(user_id=user_id, db_path=db_path):
        action_decision = "BLOCK"
        intervention_title = "Outgoing transfers are frozen (panic mode)"
        intervention_guidance = [
            "Panic freeze is active for this account.",
            "Unfreeze or wait until freeze period ends to continue.",
        ]
        status = "BLOCKED_PANIC_FREEZE"
        sync_state = "BLOCKED"
    elif force_hold:
        action_decision = "HOLD"
        intervention_title = "New device detected: transaction held for safety"
        intervention_guidance = [
            "This login was from a new device.",
            "Hold the transfer until the device is confirmed or until night sync review.",
        ] + list(intervention_guidance)
        status = "HOLD_FOR_REVIEW"
        sync_state = "HOLD"
    elif action_decision == "HOLD":
        status = "HOLD_FOR_REVIEW"
        sync_state = "HOLD"
    elif action_decision == "BLOCK":
        status = "BLOCKED_LOCAL"
        sync_state = "BLOCKED"

    # Step-up: require trusted contact approval when risk is high
    if trusted_contact and action_decision in {"HOLD", "BLOCK"} and status.startswith("HOLD"):
        approval_required = True
        approval_code_for_demo = f"{randbelow(1_000_000):06d}"
        approval_code_hash = hashlib.sha256(approval_code_for_demo.encode("utf-8")).hexdigest()
        approval_expires_at = (datetime.now(UTC) + timedelta(minutes=APPROVAL_EXPIRY_MINUTES)).isoformat()
        trusted_contact_hint = trusted_contact[-4:] if len(trusted_contact) >= 4 else trusted_contact
        status = "AWAITING_TRUSTED_APPROVAL"
        sync_state = "HOLD"
        intervention_guidance = intervention_guidance + [
            f"Approval code required from trusted contact ending with {trusted_contact_hint}.",
            f"Code expires in {APPROVAL_EXPIRY_MINUTES} minutes.",
        ]

    # Encrypt sensitive fields before storing locally
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
    # Sign the record to detect tampering later
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
    # Encrypt outbox payload for later sync
    outbox_payload = encrypt_payload(canonical_json(outbox_packet), enc_key)
    idempotency_key = hashlib.sha256(tx_id.encode("utf-8")).hexdigest()

    # Persist into transactions table + outbox queue
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (
                tx_id, user_id, amount_enc, recipient_enc, timestamp,
                risk_score, risk_level, reason_codes, action_decision, intervention_data,
                approval_required, approval_code_hash, approval_expires_at, approval_attempts,
                trusted_contact_hint, status, signature, nonce
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                1 if approval_required else 0,
                approval_code_hash,
                approval_expires_at,
                approval_attempts,
                trusted_contact_hint,
                status,
                signature,
                amount_payload["nonce"],
            ),
        )
        # Only queue for sync if it isn't blocked
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

    # Audit chain (tamper-evidence)
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

    # Change log (old/new values)
    log_change(
        entity_type="transaction",
        entity_id=tx_id,
        field_name="status",
        old_value="",
        new_value=status,
        actor=user_id,
        source="transaction_create",
        db_path=db_path,
    )
    log_change(
        entity_type="transaction",
        entity_id=tx_id,
        field_name="amount",
        old_value="",
        new_value=f"{amount:.2f}",
        actor=user_id,
        source="transaction_create",
        db_path=db_path,
    )
    log_change(
        entity_type="transaction",
        entity_id=tx_id,
        field_name="recipient",
        old_value="",
        new_value=recipient.strip(),
        actor=user_id,
        source="transaction_create",
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
        approval_required=approval_required,
        trusted_contact_hint=trusted_contact_hint,
        approval_code_for_demo=approval_code_for_demo,
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
                   risk_score, risk_level, reason_codes, action_decision, intervention_data,
                   approval_required, trusted_contact_hint, approval_expires_at, approval_attempts, status, signature
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
        approval_required,
        trusted_contact_hint,
        approval_expires_at,
        approval_attempts,
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
        "approval_required": bool(approval_required),
        "trusted_contact_hint": trusted_contact_hint or "",
        "approval_expires_at": approval_expires_at or "",
        "approval_attempts": int(approval_attempts or 0),
        "status": status,
    }


def list_secure_transactions(
    user_id: str,
    pin: str,
    db_path: Path = DB_PATH,
    limit: int = 20,
) -> list[dict]:
    """List and decrypt recent user transactions with integrity checks."""
    # Authentication and key derivation
    init_db(db_path)
    session_key = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    enc_key, sig_key = derive_crypto_keys(session_key)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT tx_id, amount_enc, recipient_enc, timestamp, risk_score, risk_level, status, signature
                   ,reason_codes, action_decision, intervention_data, approval_required, trusted_contact_hint
                   ,approval_expires_at, approval_attempts
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
            approval_required,
            trusted_contact_hint,
            approval_expires_at,
            approval_attempts,
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
        # Verify signature to detect local tampering
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
                    "approval_required": bool(approval_required),
                    "trusted_contact_hint": trusted_contact_hint or "",
                    "approval_expires_at": approval_expires_at or "",
                    "approval_attempts": int(approval_attempts or 0),
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
                "approval_required": bool(approval_required),
                "trusted_contact_hint": trusted_contact_hint or "",
                "approval_expires_at": approval_expires_at or "",
                "approval_attempts": int(approval_attempts or 0),
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
            "SELECT COUNT(*) FROM transactions WHERE status IN ('HOLD_FOR_REVIEW','AWAITING_TRUSTED_APPROVAL')"
        )
        held_count = int(cursor.fetchone()[0])

        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE status LIKE 'BLOCKED_%' OR status = 'BLOCKED_LOCAL'"
        )
        blocked_count = int(cursor.fetchone()[0])

        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE risk_level = 'HIGH' OR risk_score >= 70"
        )
        high_risk_count = int(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM audit_log")
        audit_events = int(cursor.fetchone()[0])

        cursor.execute("SELECT COUNT(*) FROM audit_log WHERE event_type = 'TRANSACTION_RELEASED'")
        released_count = int(cursor.fetchone()[0])

    return {
        "user_count": user_count,
        "tx_count": tx_count,
        "pending_count": pending_count,
        "synced_count": synced_count,
        "held_count": held_count,
        "blocked_count": blocked_count,
        "released_count": released_count,
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
    approval_code: str = "",
    db_path: Path = DB_PATH,
) -> bool:
    """Release one held transaction after successful user authentication."""
    # Verify user PIN and trusted approval code (if required).
    init_db(db_path)
    session_key = derive_session_key(user_id=user_id, pin=pin, db_path=db_path)
    _, sig_key = derive_crypto_keys(session_key)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT amount_enc, recipient_enc, timestamp, risk_score, risk_level, status,
                   approval_required, approval_code_hash, approval_expires_at, approval_attempts
            FROM transactions WHERE tx_id = ? AND user_id = ?
            """,
            (tx_id, user_id),
        )
        row = cursor.fetchone()
        if row is None:
            return False
        (
            amount_enc,
            recipient_enc,
            tx_time,
            risk_score,
            risk_level,
            status,
            approval_required,
            approval_code_hash,
            approval_expires_at,
            approval_attempts,
        ) = row
        if status not in {"HOLD_FOR_REVIEW", "AWAITING_TRUSTED_APPROVAL"}:
            return False
        if bool(approval_required):
            if int(approval_attempts or 0) >= MAX_APPROVAL_ATTEMPTS:
                cursor.execute(
                    "UPDATE transactions SET status = 'BLOCKED_TRUST_CHECK_FAILED' WHERE tx_id = ?",
                    (tx_id,),
                )
                cursor.execute(
                    "UPDATE outbox SET sync_state = 'BLOCKED' WHERE tx_id = ?",
                    (tx_id,),
                )
                conn.commit()
                return False
            if approval_expires_at:
                try:
                    if datetime.now(UTC) > datetime.fromisoformat(str(approval_expires_at)):
                        cursor.execute(
                            "UPDATE transactions SET status = 'BLOCKED_APPROVAL_EXPIRED' WHERE tx_id = ?",
                            (tx_id,),
                        )
                        cursor.execute(
                            "UPDATE outbox SET sync_state = 'BLOCKED' WHERE tx_id = ?",
                            (tx_id,),
                        )
                        conn.commit()
                        return False
                except ValueError:
                    pass
            provided_hash = hashlib.sha256(approval_code.strip().encode("utf-8")).hexdigest()
            if not approval_code.strip() or provided_hash != (approval_code_hash or ""):
                cursor.execute(
                    "UPDATE transactions SET approval_attempts = approval_attempts + 1 WHERE tx_id = ?",
                    (tx_id,),
                )
                conn.commit()
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
            """
            UPDATE transactions
            SET status = ?, signature = ?, approval_required = 0,
                approval_code_hash = NULL, approval_expires_at = NULL, approval_attempts = 0
            WHERE tx_id = ?
            """,
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
    log_change(
        entity_type="transaction",
        entity_id=tx_id,
        field_name="status",
        old_value=status,
        new_value=new_status,
        actor=user_id,
        source="release_held_transaction",
        db_path=db_path,
    )
    return True
