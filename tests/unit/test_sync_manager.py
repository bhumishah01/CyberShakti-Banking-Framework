import sqlite3
from datetime import UTC, datetime

from src.auth.service import create_user
from src.database.init_db import init_db
from src.database.transaction_store import create_secure_transaction
from src.sync.manager import sync_outbox


def test_sync_outbox_success_marks_transaction_synced(tmp_path) -> None:
    db_path = tmp_path / "sync.db"
    init_db(db_path)
    create_user("u300", "+919111111111", "1234", db_path=db_path)

    stored = create_secure_transaction(
        user_id="u300",
        pin="1234",
        amount=500.0,
        recipient="Kiran",
        db_path=db_path,
        timestamp=datetime(2026, 2, 23, 13, 0, tzinfo=UTC),
    )

    def sender(_packet: dict) -> dict:
        return {"status": "synced"}

    summary = sync_outbox(db_path=db_path, sender=sender)
    assert summary.processed == 1
    assert summary.synced == 1
    assert summary.duplicates == 0
    assert summary.retried == 0

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sync_state, last_error FROM outbox WHERE outbox_id = ?", (stored.outbox_id,))
        outbox_state, last_error = cursor.fetchone()
        assert outbox_state == "SYNCED"
        assert last_error is None

        cursor.execute("SELECT status FROM transactions WHERE tx_id = ?", (stored.tx_id,))
        tx_status = cursor.fetchone()[0]
        assert tx_status == "SYNCED"


def test_sync_outbox_duplicate_ack_marks_duplicate_state(tmp_path) -> None:
    db_path = tmp_path / "sync.db"
    init_db(db_path)
    create_user("u301", "+919222222222", "1234", db_path=db_path)

    stored = create_secure_transaction(
        user_id="u301",
        pin="1234",
        amount=1200.0,
        recipient="Meera",
        db_path=db_path,
        timestamp=datetime(2026, 2, 23, 13, 0, tzinfo=UTC),
    )

    def sender(_packet: dict) -> dict:
        return {"status": "duplicate"}

    summary = sync_outbox(db_path=db_path, sender=sender)
    assert summary.processed == 1
    assert summary.synced == 0
    assert summary.duplicates == 1
    assert summary.retried == 0

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT sync_state FROM outbox WHERE outbox_id = ?", (stored.outbox_id,))
        outbox_state = cursor.fetchone()[0]
        assert outbox_state == "SYNCED_DUPLICATE_ACK"

        cursor.execute("SELECT status FROM transactions WHERE tx_id = ?", (stored.tx_id,))
        tx_status = cursor.fetchone()[0]
        assert tx_status == "SYNCED_DUPLICATE_ACK"


def test_sync_outbox_failure_sets_retry_and_backoff(tmp_path) -> None:
    db_path = tmp_path / "sync.db"
    init_db(db_path)
    create_user("u302", "+919333333333", "1234", db_path=db_path)

    stored = create_secure_transaction(
        user_id="u302",
        pin="1234",
        amount=700.0,
        recipient="Sana",
        db_path=db_path,
        timestamp=datetime(2026, 2, 23, 13, 0, tzinfo=UTC),
    )

    now = datetime(2026, 2, 23, 14, 0, tzinfo=UTC)

    def sender(_packet: dict) -> dict:
        raise RuntimeError("network unavailable")

    summary = sync_outbox(db_path=db_path, sender=sender, now=now)
    assert summary.processed == 1
    assert summary.synced == 0
    assert summary.duplicates == 0
    assert summary.retried == 1

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sync_state, retry_count, next_retry_at, last_error FROM outbox WHERE outbox_id = ?",
            (stored.outbox_id,),
        )
        sync_state, retry_count, next_retry_at, last_error = cursor.fetchone()
        assert sync_state == "RETRYING"
        assert retry_count == 1
        assert next_retry_at is not None
        assert "network unavailable" in last_error

        cursor.execute("SELECT status FROM transactions WHERE tx_id = ?", (stored.tx_id,))
        tx_status = cursor.fetchone()[0]
        assert tx_status == "RETRYING_SYNC"
