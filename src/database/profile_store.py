"""User behavior profiling (offline-first).

Tracks per-user baseline behavior to support adaptive fraud scoring:
- average amount
- transaction frequency (via last_tx_at)
- preferred hours of usage (hour histogram)

This data stays local in SQLite and is lightweight enough for low-end devices.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from src.database.init_db import DB_PATH, init_db


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    tx_count: int
    total_amount: float
    avg_amount: float
    last_tx_at: str
    hour_hist: dict
    user_risk_score: int


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def get_or_create_profile(user_id: str, db_path: Path = DB_PATH) -> UserProfile:
    init_db(db_path)
    user_id = user_id.strip()
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT tx_count, total_amount, avg_amount, last_tx_at, hour_hist, user_risk_score
            FROM user_profiles WHERE user_id = ?
            """,
            (user_id,),
        )
        row = cursor.fetchone()

        if row is None:
            # Create empty profile. (We keep it cheap; no backfill scanning.)
            cursor.execute(
                """
                INSERT INTO user_profiles (
                    user_id, tx_count, total_amount, avg_amount, last_tx_at, hour_hist, user_risk_score, updated_at
                ) VALUES (?, 0, 0.0, 0.0, '', ?, 0, ?)
                """,
                (user_id, json.dumps({}), _now_iso()),
            )
            conn.commit()
            return UserProfile(
                user_id=user_id,
                tx_count=0,
                total_amount=0.0,
                avg_amount=0.0,
                last_tx_at="",
                hour_hist={},
                user_risk_score=0,
            )

    tx_count, total_amount, avg_amount, last_tx_at, hour_hist_raw, user_risk_score = row
    try:
        hour_hist = json.loads(hour_hist_raw or "{}")
    except Exception:
        hour_hist = {}
    if not isinstance(hour_hist, dict):
        hour_hist = {}
    return UserProfile(
        user_id=user_id,
        tx_count=int(tx_count or 0),
        total_amount=float(total_amount or 0.0),
        avg_amount=float(avg_amount or 0.0),
        last_tx_at=str(last_tx_at or ""),
        hour_hist=hour_hist,
        user_risk_score=int(user_risk_score or 0),
    )


def update_profile_after_tx(
    *,
    user_id: str,
    amount: float,
    timestamp_iso: str,
    tx_risk_score: int,
    db_path: Path = DB_PATH,
) -> UserProfile:
    """Update profile incrementally (O(1)) after a transaction is created."""
    init_db(db_path)
    user_id = user_id.strip()
    profile = get_or_create_profile(user_id, db_path=db_path)

    new_tx_count = profile.tx_count + 1
    new_total = float(profile.total_amount) + float(amount)
    new_avg = new_total / new_tx_count if new_tx_count > 0 else 0.0

    # Hour histogram (preferred usage time)
    hour_hist = dict(profile.hour_hist or {})
    try:
        hour = datetime.fromisoformat(timestamp_iso).hour
    except Exception:
        hour = -1
    if 0 <= hour <= 23:
        hour_hist[str(hour)] = int(hour_hist.get(str(hour), 0)) + 1

    # Per-user risk score: EWMA (keeps it stable + explainable)
    prev = int(profile.user_risk_score)
    new_user_risk = int(round(0.7 * prev + 0.3 * int(tx_risk_score))) if new_tx_count > 1 else int(tx_risk_score)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE user_profiles
            SET tx_count = ?, total_amount = ?, avg_amount = ?, last_tx_at = ?, hour_hist = ?,
                user_risk_score = ?, updated_at = ?
            WHERE user_id = ?
            """,
            (
                int(new_tx_count),
                float(new_total),
                float(new_avg),
                str(timestamp_iso),
                json.dumps(hour_hist),
                int(new_user_risk),
                _now_iso(),
                user_id,
            ),
        )
        conn.commit()

    return UserProfile(
        user_id=user_id,
        tx_count=new_tx_count,
        total_amount=new_total,
        avg_amount=new_avg,
        last_tx_at=str(timestamp_iso),
        hour_hist=hour_hist,
        user_risk_score=new_user_risk,
    )


def preferred_hours(profile: UserProfile, top_n: int = 3) -> list[int]:
    hist = profile.hour_hist or {}
    items = []
    for k, v in hist.items():
        try:
            hour = int(k)
            count = int(v)
        except Exception:
            continue
        if 0 <= hour <= 23 and count > 0:
            items.append((count, hour))
    items.sort(reverse=True)
    return [hour for _, hour in items[: max(0, int(top_n))]]

