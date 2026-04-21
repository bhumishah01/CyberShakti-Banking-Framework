# STEP 20 - Offline Sync Queue + Night Sync Simulator

## What Was Added
- New UI page to visualize the local outbox queue (pending/retrying/synced/held/blocked).
- Dashboard link to open the Sync Queue.
- Button to simulate a “night sync” that marks pending outbox entries as synced.

## Why This Matters
- Demonstrates offline-first behavior and delayed sync for low-connectivity users.
- Easy to explain in a demo: data stays local, then syncs safely later.

## How To Use
- Open the dashboard and click **Open Sync Queue**.
- Click **Simulate Night Sync** to move pending records to synced.

## Files Updated
- `src/ui/app.py`
- `src/ui/templates/index.html`
- `src/ui/templates/sync_queue.html`
