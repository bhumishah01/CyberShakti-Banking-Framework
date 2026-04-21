# STEP 38: Sync Queue (Selective Sync + Release Held + Better Layout)

## Goal
Make offline-first syncing demo-ready and realistic:
- show transactions stored locally
- sync later when network is available
- allow control:
  - sync one
  - sync selected
  - sync all
- release held transactions intentionally (review workflow)

## What Was Implemented

### 1) Sync Selected / Sync One / Sync All
Admin can:
- sync a specific outbox record
- pick multiple records and sync selected
- sync all pending items

This matches rural conditions where bank staff may sync in batches.

### 2) Release Held Transactions (Per Transaction)
Held transactions can be released:
- chosen transaction only (no forced “sync all”)
- then it becomes eligible to sync

### 3) UI Alignment Fixes
We made the page readable:
- truncated IDs
- tooltips for full UUID
- stable column layout (no wrapping)

## Where To See It
- Sync queue: `/sync/queue`

## Key Files
- Routes: `src/ui/app.py`
- Template: `src/ui/templates/sync_queue.html`
- Sync manager: `src/sync/manager.py`

