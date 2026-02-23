import sqlite3
from datetime import UTC, datetime

import pytest

from src.auth.service import create_user
from src.database.init_db import init_db
from src.database.transaction_store import (
    create_secure_transaction,
    list_secure_transactions,
    read_secure_transaction,
)


def test_secure_transaction_is_encrypted_and_retrievable(tmp_path) -> None:
    db_path = tmp_path / "tx.db"
    init_db(db_path)
    create_user("u100", "+919123456789", "1234", db_path=db_path)

    stored = create_secure_transaction(
        user_id="u100",
        pin="1234",
        amount=2500.75,
        recipient="Ravi Kumar",
        db_path=db_path,
        timestamp=datetime(2026, 2, 23, 13, 0, tzinfo=UTC),
    )
    assert stored.risk_score == 20
    assert stored.risk_level == "LOW"
    assert "NEW_RECIPIENT" in stored.reason_codes

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT amount_enc, recipient_enc, status FROM transactions WHERE tx_id = ?",
            (stored.tx_id,),
        )
        tx_row = cursor.fetchone()
        assert tx_row is not None
        amount_enc, recipient_enc, status = tx_row

        assert "2500.75" not in amount_enc
        assert "Ravi Kumar" not in recipient_enc
        assert status == "PENDING"

        cursor.execute(
            "SELECT payload_enc, sync_state FROM outbox WHERE outbox_id = ?",
            (stored.outbox_id,),
        )
        outbox_row = cursor.fetchone()
        assert outbox_row is not None
        payload_enc, sync_state = outbox_row
        assert "Ravi Kumar" not in payload_enc
        assert sync_state == "PENDING"

        cursor.execute("SELECT event_type FROM audit_log ORDER BY created_at ASC, rowid ASC")
        audit_rows = cursor.fetchall()
        assert audit_rows
        assert audit_rows[-1][0] == "TRANSACTION_CREATED"

    decrypted = read_secure_transaction(stored.tx_id, "u100", "1234", db_path=db_path)
    assert decrypted["amount"] == "2500.75"
    assert decrypted["recipient"] == "Ravi Kumar"
    assert "NEW_RECIPIENT" in decrypted["reason_codes"]

    listed = list_secure_transactions("u100", "1234", db_path=db_path, limit=5)
    assert listed
    assert "NEW_RECIPIENT" in listed[0]["reason_codes"]


def test_transaction_tampering_is_detected(tmp_path) -> None:
    db_path = tmp_path / "tx.db"
    init_db(db_path)
    create_user("u200", "+919000000000", "5678", db_path=db_path)

    stored = create_secure_transaction(
        user_id="u200",
        pin="5678",
        amount=99.00,
        recipient="Asha",
        db_path=db_path,
        timestamp=datetime(2026, 2, 23, 13, 0, tzinfo=UTC),
    )

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET amount_enc = ? WHERE tx_id = ?",
            ("{\"nonce\":\"abc\",\"ciphertext\":\"tampered\"}", stored.tx_id),
        )
        conn.commit()

    with pytest.raises(ValueError, match="integrity"):
        read_secure_transaction(stored.tx_id, "u200", "5678", db_path=db_path)
