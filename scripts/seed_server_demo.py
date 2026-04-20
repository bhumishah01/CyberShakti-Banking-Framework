"""Seed Postgres-backed Server API with sample users + transactions.

Usage (example):
  export DATABASE_URL='postgresql+psycopg://ruralshield:ruralshield_dev@localhost:5432/ruralshield'
  export JWT_SECRET='dev-change-me'
  export FIELD_ENC_KEY='dev-change-me-to-32chars-minimum'
  python scripts/seed_server_demo.py
"""

from __future__ import annotations

import random
import uuid

from sqlalchemy.orm import Session

from src.server.db.base import Base
from src.server.db.session import get_engine, get_sessionmaker
from src.server.services.auth import register_user
from src.server.services.transactions import create_transaction


def main() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    SessionLocal = get_sessionmaker()

    with SessionLocal() as db:  # type: ignore[call-arg]
        _seed_users(db)
        _seed_transactions(db)

    print("Seeded server demo data.")


def _seed_users(db: Session) -> None:
    users = [
        ("bank_admin", "+910000000001", "admin123", "bank_officer"),
        ("agent_1", "+910000000002", "agent123", "agent"),
        ("c1", "+919999000001", "1234", "customer"),
        ("c2", "+919999000002", "1234", "customer"),
        ("c3", "+919999000003", "1234", "customer"),
    ]
    for user_id, phone, password, role in users:
        try:
            register_user(db, user_id=user_id, phone=phone, password=password, role=role)
        except Exception:
            # user_exists, ignore
            pass


def _seed_transactions(db: Session) -> None:
    recipients = ["Local Merchant", "Kirana Store", "Fertilizer Shop", "School Fees", "UPI Transfer", "Unknown Payee"]
    device_ids = ["devA", "devB", "devC", ""]  # empty device id is allowed
    customers = ["c1", "c2", "c3"]

    for _ in range(18):
        user_id = random.choice(customers)
        amount = random.choice([120, 350, 999, 1850, 2900, 4200, 7500])
        recipient = random.choice(recipients)
        device_id = random.choice(device_ids)
        idem = f"seed:{uuid.uuid4().hex}"
        create_transaction(
            db,
            user_id=user_id,
            amount=float(amount),
            recipient=recipient,
            device_id=device_id,
            idempotency_key=idem,
        )


if __name__ == "__main__":
    main()

