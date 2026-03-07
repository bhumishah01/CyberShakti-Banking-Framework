"""Database initialization for RuralShield local-first storage."""

from __future__ import annotations

import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "ruralshield.db"


def init_db(db_path: Path = DB_PATH) -> None:
    """Create local SQLite schema if it does not already exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                phone_hash TEXT NOT NULL,
                pin_salt TEXT NOT NULL,
                pin_hash TEXT NOT NULL,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                lockout_until TEXT,
                last_auth_at TEXT,
                auth_config TEXT,
                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                masked_account_no TEXT NOT NULL,
                metadata_enc TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount_enc TEXT NOT NULL,
                recipient_enc TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                reason_codes TEXT,
                action_decision TEXT,
                intervention_data TEXT,
                approval_required INTEGER NOT NULL DEFAULT 0,
                approval_code_hash TEXT,
                approval_expires_at TEXT,
                approval_attempts INTEGER NOT NULL DEFAULT 0,
                trusted_contact_hint TEXT,
                status TEXT NOT NULL,
                signature TEXT NOT NULL,
                nonce TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
                outbox_id TEXT PRIMARY KEY,
                tx_id TEXT NOT NULL,
                idempotency_key TEXT,
                payload_enc TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_at TEXT,
                last_error TEXT,
                sync_state TEXT NOT NULL,
                FOREIGN KEY (tx_id) REFERENCES transactions (tx_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS fraud_rules (
                rule_id TEXT PRIMARY KEY,
                rule_version TEXT NOT NULL,
                rule_data TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                event_data_enc TEXT NOT NULL,
                prev_hash TEXT,
                curr_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scenario_runs (
                run_id TEXT PRIMARY KEY,
                scenario_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                tx_created INTEGER NOT NULL,
                high_risk_count INTEGER NOT NULL,
                held_count INTEGER NOT NULL,
                blocked_count INTEGER NOT NULL,
                avg_risk_score REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        _ensure_users_auth_columns(cursor)
        _ensure_outbox_sync_columns(cursor)
        _ensure_transactions_columns(cursor)
        conn.commit()


def _ensure_users_auth_columns(cursor: sqlite3.Cursor) -> None:
    """Backfill auth columns for older local databases."""
    cursor.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cursor.fetchall()}

    if "failed_attempts" not in columns:
        cursor.execute(
            "ALTER TABLE users ADD COLUMN failed_attempts INTEGER NOT NULL DEFAULT 0"
        )
    if "lockout_until" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN lockout_until TEXT")
    if "last_auth_at" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN last_auth_at TEXT")


def _ensure_outbox_sync_columns(cursor: sqlite3.Cursor) -> None:
    """Backfill sync columns for older local databases."""
    cursor.execute("PRAGMA table_info(outbox)")
    columns = {row[1] for row in cursor.fetchall()}

    if "idempotency_key" not in columns:
        cursor.execute("ALTER TABLE outbox ADD COLUMN idempotency_key TEXT")
    if "last_error" not in columns:
        cursor.execute("ALTER TABLE outbox ADD COLUMN last_error TEXT")


def _ensure_transactions_columns(cursor: sqlite3.Cursor) -> None:
    """Backfill transaction columns added after initial schema."""
    cursor.execute("PRAGMA table_info(transactions)")
    columns = {row[1] for row in cursor.fetchall()}

    if "reason_codes" not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN reason_codes TEXT")
    if "action_decision" not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN action_decision TEXT")
    if "intervention_data" not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN intervention_data TEXT")
    if "approval_required" not in columns:
        cursor.execute(
            "ALTER TABLE transactions ADD COLUMN approval_required INTEGER NOT NULL DEFAULT 0"
        )
    if "approval_code_hash" not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN approval_code_hash TEXT")
    if "approval_expires_at" not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN approval_expires_at TEXT")
    if "approval_attempts" not in columns:
        cursor.execute(
            "ALTER TABLE transactions ADD COLUMN approval_attempts INTEGER NOT NULL DEFAULT 0"
        )
    if "trusted_contact_hint" not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN trusted_contact_hint TEXT")


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at: {DB_PATH}")
