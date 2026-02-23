"""Secure local transaction persistence for offline-first flow."""

from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

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


@dataclass(frozen=True)
class StoredTransaction:
    tx_id: str
    outbox_id: str
    status: str
    sync_state: str
    signature: str


def create_secure_transaction(
    user_id: str,
    pin: str,
    amount: float,
    recipient: str,
    db_path: Path = DB_PATH,
    risk_score: int = 0,
    risk_level: str = "LOW",
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
        "amount_enc": amount_enc,
        "recipient_enc": recipient_enc,
        "signature": signature,
    }
    outbox_payload = encrypt_payload(canonical_json(outbox_packet), enc_key)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO transactions (
                tx_id, user_id, amount_enc, recipient_enc, timestamp,
                risk_score, risk_level, status, signature, nonce
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                tx_id,
                user_id,
                amount_enc,
                recipient_enc,
                tx_time,
                risk_score,
                risk_level,
                status,
                signature,
                amount_payload["nonce"],
            ),
        )

        cursor.execute(
            """
            INSERT INTO outbox (
                outbox_id, tx_id, payload_enc, retry_count, next_retry_at, sync_state
            ) VALUES (?, ?, ?, 0, NULL, ?)
            """,
            (outbox_id, tx_id, canonical_json(outbox_payload), sync_state),
        )
        conn.commit()

    return StoredTransaction(
        tx_id=tx_id,
        outbox_id=outbox_id,
        status=status,
        sync_state=sync_state,
        signature=signature,
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
                   risk_score, risk_level, status, signature
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
        "status": status,
    }
