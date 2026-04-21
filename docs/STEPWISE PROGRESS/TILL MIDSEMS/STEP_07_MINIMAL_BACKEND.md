# Step 7: Minimal Backend Sync API

## What was implemented

- FastAPI backend in `src/backend/app.py`.
- HTTP sync client adapter in `src/sync/client.py`.
- Rule fetch/update endpoints for fraud rule distribution.

## Endpoints

- `GET /health`
  - service health check.
- `POST /sync/transactions`
  - accepts encrypted transaction packets,
  - returns `synced` for first idempotency key,
  - returns `duplicate` for repeat idempotency key.
- `GET /rules`
  - returns active fraud rule set.
- `POST /rules`
  - upserts fraud rules.

## Integration role

- `sync_outbox(...)` can use HTTP sender from `make_http_sender(...)`.
- This enables realistic local demo flow for delayed sync + duplicate handling.

## Tests added

- `tests/unit/test_backend_api.py`
  - health endpoint,
  - sync duplicate handling,
  - rule update/list checks.
- `tests/unit/test_sync_client.py`
  - HTTP sender payload behavior,
  - rule fetch behavior.

Result in current environment: `15 passed, 1 skipped`.
(`fastapi` tests are skipped only when dependency is not installed in runtime.)

## Local run command

```bash
uvicorn src.backend.app:app --host 0.0.0.0 --port 8000 --reload
```
