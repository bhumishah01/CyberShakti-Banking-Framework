# STEP 02: Offline Sync Engine UI (Outbox Queue + Manual Controls)

## Goal
Show the “offline-first” banking idea clearly:
- transactions are stored locally (SQLite)
- they enter an **outbox queue**
- sync happens later (night / network available)
- staff can sync one, many, or all records (rural workflow)

## What Was Implemented

### Sync Queue Page
Created a dedicated sync queue page:
- URL: `/sync/queue`
- Reads local SQLite `outbox` + joins `transactions` for user/status.

### Sync Controls
From Sync Queue, admin can now:
- Sync all pending records (POST `/sync`)
- Sync one record (POST `/sync/one`)
- Sync selected rows (POST `/sync/selected`)

### Release Held Transactions (from Queue)
If a transaction is held, admin can release it from the queue:
- POST `/transactions/release`
- After release: outbox becomes `PENDING` and tx status becomes `PENDING`

### Persistence + UX fixes
- Server URL is remembered (cookie) so admin does not keep retyping it.
- Pages render with `Cache-Control: no-store` so state updates after actions.
- Improved alignment and truncation (IDs display short with tooltips).

## Demo URLs
- Sync Queue: `/sync/queue`
- Release held is available inline per row when `sync_state=HOLD`

## Key Files
- Routes: `src/ui/app.py`
- Sync queue template: `src/ui/templates/sync_queue.html`
- Sync manager: `src/sync/manager.py`
- HTTP sender adapter: `src/sync/client.py`

## Why This Matters
This demonstrates a realistic rural constraint:
“limited connectivity” does not break banking workflows.
Instead, we **queue**, **protect**, and **sync later**.

