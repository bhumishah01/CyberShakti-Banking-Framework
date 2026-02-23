# Step 10: Web Interface (Non-CLI Demo)

## Goal

Provide a proper runnable interface for demo and evaluation without command-line interaction.

## What was implemented

- FastAPI-based web dashboard: `src/ui/app.py`
- HTML templates:
  - `src/ui/templates/index.html`
  - `src/ui/templates/transactions.html`
- CSS styling:
  - `src/ui/static/styles.css`

## Features in the web UI

- Register/replace user.
- Create secure transaction.
- View decrypted transaction list with risk + status.
- Sync pending transactions with backend server URL input.
- Check audit chain integrity.

## Run command

```bash
uvicorn src.ui.app:app --host 0.0.0.0 --port 8501 --reload
```

Open in browser:
- `http://localhost:8501`

## Test coverage

- `tests/unit/test_ui_app.py`
  - page load,
  - user creation,
  - transaction creation,
  - transaction list rendering.
