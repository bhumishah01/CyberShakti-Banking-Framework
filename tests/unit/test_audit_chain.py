import sqlite3
from datetime import UTC, datetime

from src.audit.chain import append_audit_event, verify_audit_chain
from src.database.init_db import init_db


def test_audit_chain_valid_for_linked_entries(tmp_path) -> None:
    db_path = tmp_path / "audit.db"
    init_db(db_path)

    append_audit_event(
        event_type="TEST_EVENT_1",
        event_data_enc="payload-one",
        db_path=db_path,
        created_at=datetime(2026, 2, 23, 12, 0, tzinfo=UTC),
    )
    append_audit_event(
        event_type="TEST_EVENT_2",
        event_data_enc="payload-two",
        db_path=db_path,
        created_at=datetime(2026, 2, 23, 12, 1, tzinfo=UTC),
    )

    result = verify_audit_chain(db_path=db_path)
    assert result.is_valid is True
    assert result.checked_entries == 2
    assert result.error is None


def test_audit_chain_detects_tampering(tmp_path) -> None:
    db_path = tmp_path / "audit.db"
    init_db(db_path)

    entry = append_audit_event(
        event_type="TEST_EVENT",
        event_data_enc="original",
        db_path=db_path,
        created_at=datetime(2026, 2, 23, 12, 0, tzinfo=UTC),
    )

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE audit_log SET event_data_enc = ? WHERE log_id = ?",
            ("tampered", entry.log_id),
        )
        conn.commit()

    result = verify_audit_chain(db_path=db_path)
    assert result.is_valid is False
    assert result.error is not None
    assert "Hash mismatch" in result.error
