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
                payload_enc TEXT NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                next_retry_at TEXT,
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

        conn.commit()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at: {DB_PATH}")
