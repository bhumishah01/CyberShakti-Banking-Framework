"""Local device trust tracking (offline-first)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from src.database.init_db import DB_PATH, init_db


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def upsert_device(
    *,
    user_id: str,
    device_id: str,
    is_trusted: bool,
    db_path: Path = DB_PATH,
) -> None:
    """Record a device sighting for a user."""
    init_db(db_path)
    user_id = user_id.strip()
    device_id = device_id.strip()
    if not user_id or not device_id:
        return

    now = _now_iso()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT is_trusted, seen_count
            FROM devices
            WHERE user_id = ? AND device_id = ?
            """,
            (user_id, device_id),
        )
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                """
                INSERT INTO devices (
                    user_id, device_id, is_trusted, first_seen, last_seen, seen_count
                ) VALUES (?, ?, ?, ?, ?, 1)
                """,
                (user_id, device_id, 1 if is_trusted else 0, now, now),
            )
        else:
            prev_trusted, prev_seen = row
            cursor.execute(
                """
                UPDATE devices
                SET is_trusted = ?, last_seen = ?, seen_count = ?
                WHERE user_id = ? AND device_id = ?
                """,
                (
                    1 if (bool(prev_trusted) or is_trusted) else 0,
                    now,
                    int(prev_seen or 0) + 1,
                    user_id,
                    device_id,
                ),
            )
        conn.commit()


def list_devices(db_path: Path = DB_PATH, limit: int = 50) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, device_id, is_trusted, first_seen, last_seen, seen_count
            FROM devices
            ORDER BY last_seen DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cursor.fetchall()
    items = []
    for user_id, device_id, is_trusted, first_seen, last_seen, seen_count in rows:
        items.append(
            {
                "user_id": user_id,
                "device_id": device_id,
                "is_trusted": bool(is_trusted),
                "first_seen": first_seen,
                "last_seen": last_seen,
                "seen_count": int(seen_count or 0),
            }
        )
    return items

