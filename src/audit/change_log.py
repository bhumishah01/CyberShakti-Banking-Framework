"""Change log capture for local-first audit visibility."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from src.database.init_db import DB_PATH, init_db


def log_change(
    *,
    entity_type: str,
    entity_id: str,
    field_name: str,
    old_value: object,
    new_value: object,
    actor: str,
    source: str,
    db_path: Path = DB_PATH,
) -> None:
    init_db(db_path)
    payload_old = json.dumps(old_value, ensure_ascii=True)
    payload_new = json.dumps(new_value, ensure_ascii=True)
    with sqlite3.connect(db_path, timeout=5) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO change_log (
                log_id, entity_type, entity_id, field_name,
                old_value, new_value, actor, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                entity_type,
                entity_id,
                field_name,
                payload_old,
                payload_new,
                actor,
                source,
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
