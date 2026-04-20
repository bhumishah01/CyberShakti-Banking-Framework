"""Local alerts + notifications store (offline-first).

This is used to:
- surface suspicious-pattern alerts in the bank portal
- show notifications to customers (held/blocked/success)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from src.database.init_db import DB_PATH, init_db


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def create_alert(
    *,
    alert_type: str,
    severity: str,
    message: str,
    user_id: str | None = None,
    metadata: dict | None = None,
    db_path: Path = DB_PATH,
) -> str:
    """Create a suspicious-pattern alert (for admin/bank dashboards)."""
    init_db(db_path)
    alert_id = str(uuid.uuid4())
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alerts (
                alert_id, user_id, alert_type, severity, message, metadata_json, acknowledged, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                alert_id,
                (user_id or "").strip() or None,
                str(alert_type),
                str(severity),
                str(message),
                json.dumps(metadata or {}),
                _now_iso(),
            ),
        )
        conn.commit()
    return alert_id


def create_notification(
    *,
    notif_type: str,
    title: str,
    body: str,
    role: str,
    user_id: str | None = None,
    db_path: Path = DB_PATH,
) -> str:
    """Create a notification (customer/bank)."""
    init_db(db_path)
    notification_id = str(uuid.uuid4())
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO notifications (
                notification_id, user_id, role, notif_type, title, body, is_read, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                notification_id,
                (user_id or "").strip() or None,
                str(role),
                str(notif_type),
                str(title),
                str(body),
                _now_iso(),
            ),
        )
        conn.commit()
    return notification_id


def list_recent_alerts(db_path: Path = DB_PATH, limit: int = 20) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT alert_id, user_id, alert_type, severity, message, metadata_json, acknowledged, created_at
            FROM alerts
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (int(limit),),
        )
        rows = cursor.fetchall()
    items = []
    for alert_id, user_id, alert_type, severity, message, metadata_json, acknowledged, created_at in rows:
        try:
            meta = json.loads(metadata_json or "{}")
        except Exception:
            meta = {}
        items.append(
            {
                "alert_id": alert_id,
                "user_id": user_id or "",
                "alert_type": alert_type,
                "severity": severity,
                "message": message,
                "metadata": meta if isinstance(meta, dict) else {},
                "acknowledged": bool(acknowledged),
                "created_at": created_at,
            }
        )
    return items


def list_notifications(
    *,
    role: str,
    user_id: str | None = None,
    db_path: Path = DB_PATH,
    limit: int = 20,
) -> list[dict]:
    init_db(db_path)
    params: list = [str(role)]
    where = "role = ?"
    if user_id:
        where += " AND (user_id = ? OR user_id IS NULL)"
        params.append(user_id.strip())
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT notification_id, user_id, notif_type, title, body, is_read, created_at
            FROM notifications
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (*params, int(limit)),
        )
        rows = cursor.fetchall()
    items = []
    for nid, uid, ntype, title, body, is_read, created_at in rows:
        items.append(
            {
                "notification_id": nid,
                "user_id": uid or "",
                "notif_type": ntype,
                "title": title,
                "body": body,
                "is_read": bool(is_read),
                "created_at": created_at,
            }
        )
    return items

