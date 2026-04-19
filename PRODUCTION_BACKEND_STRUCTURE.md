# RuralShield Production Backend Upgrade (Server API)

This document describes the production-style backend we added alongside the existing offline-first UI prototype.

## High-Level Structure

```
src/server/
  app.py                # FastAPI app (server API)
  core/
    config.py           # env settings (JWT + DB + encryption keys)
    security.py         # JWT + password hashing + field encryption helpers
  db/
    base.py             # SQLAlchemy Base
    session.py          # engine + SessionLocal + dependency
  models/
    user.py             # users table
    device.py           # devices table (device binding)
    transaction.py      # transactions table
    fraud_log.py        # fraud_logs table
    sync.py             # sync_queue + sync_logs tables
  schemas/
    auth.py             # request/response models
    transactions.py
    sync.py
  api/
    deps.py             # JWT auth + RBAC dependencies
  services/
    auth.py             # register/login logic
    fraud.py            # behavioral profile + dynamic risk scoring
    transactions.py     # transaction creation + fraud logging
    sync.py             # outbox push + server authority policy
  routers/
    auth.py             # /auth
    transactions.py     # /transactions
    fraud.py            # /fraud
    sync.py             # /sync
    agent.py            # /agent
```

## REST Endpoints

- `/auth/register` (POST) create user (customer/bank_officer/agent)
- `/auth/login` (POST) issue JWT
- `/transactions` (POST) customer creates transaction (encrypted recipient + risk scored)
- `/sync/push` (POST) push offline outbox items to server (idempotent; queued)
- `/agent/onboard` (POST) agent creates customer
- `/agent/assisted-transaction` (POST) agent creates transaction for customer
- `/fraud/logs` (GET) bank officer views fraud logs
- `/health` (GET) health check

## PostgreSQL Schema (Logical)

Tables:
- `users(user_id pk, role, phone_hash, password_hash, created_at, updated_at)`
- `devices(device_id pk, user_id fk, trust_level, enrolled_at, last_seen_at)`
- `transactions(tx_id pk, user_id fk, device_id, amount, recipient_enc, risk_score, risk_level, reason_codes, status, idempotency_key)`
- `fraud_logs(log_id pk, tx_id, user_id fk, risk_score, risk_level, reasons_json, created_at)`
- `sync_queue(queue_id pk, user_id fk, tx_id, idempotency_key, payload_enc, state, retry_count, last_error, created_at)`
- `sync_logs(log_id pk, user_id fk, tx_id, idempotency_key, result, detail, created_at)`

Indexes: user_id, role, created_at, risk_level, sync state, idempotency_key.

## Deployment

Local (Docker Compose + Postgres):

```bash
docker compose up --build
```

Server API runs on `http://127.0.0.1:8000`.

Required env vars:
- `DATABASE_URL`
- `JWT_SECRET`
- `FIELD_ENC_KEY`

## Notes

- SQLite remains the offline-first local store used by the UI prototype.
- The server API is Postgres-backed and intended for real deployment.
- Migrations are not added yet (we auto-create tables). Next step is Alembic.

