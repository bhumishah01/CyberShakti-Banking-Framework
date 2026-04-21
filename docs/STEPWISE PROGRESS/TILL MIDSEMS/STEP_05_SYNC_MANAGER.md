# Step 5: Outbox Sync Manager (Retry + Idempotency)

## What was implemented

- Full sync manager in `src/sync/manager.py`.
- Idempotency + retry metadata support in outbox schema.
- Retry backoff workflow with sync state transitions.

## Sync behavior now

- Processes due outbox items in `PENDING` or `RETRYING` state.
- Sends encrypted payload packet with idempotency key.
- Handles acknowledgment statuses:
  - `synced` -> `SYNCED`
  - `duplicate` -> `SYNCED_DUPLICATE_ACK`
- On failures:
  - increments `retry_count`,
  - schedules `next_retry_at` using exponential backoff,
  - stores `last_error`,
  - marks state as `RETRYING`.

## DB updates

Outbox now includes:
- `idempotency_key`
- `last_error`

Migration logic updates older DBs automatically in `init_db.py`.

## Transaction state integration

- Successful sync updates transaction status to `SYNCED`.
- Duplicate ack updates status to `SYNCED_DUPLICATE_ACK`.
- Failed sync updates status to `RETRYING_SYNC`.

## Tests added

- `tests/unit/test_sync_manager.py`
  - success case,
  - duplicate-ack case,
  - failure and retry scheduling case.

Result: `11 passed`.
