# STEP 18 - Local Change Log Export (CSV/Excel)

## What Was Added
- New SQLite table `change_log` to capture old/new values for key edits.
- Change log entries written for:
  - user creation/replacement
  - transaction creation
  - transaction release (status change)
- UI button to export change log to CSV for Excel viewing.

## Why This Matters
- Demonstrates local-first storage and traceability.
- Faculty can see exact old vs new values without server connectivity.

## How To Use
- Open the dashboard and click **Export Change Log (CSV)**.
- File is saved to `data/exports/change_log_<timestamp>.csv`.

## Files Updated
- `src/database/init_db.py`
- `src/audit/change_log.py`
- `src/auth/service.py`
- `src/database/transaction_store.py`
- `src/ui/app.py`
- `src/ui/templates/index.html`
- `tests/unit/test_init_db.py`

