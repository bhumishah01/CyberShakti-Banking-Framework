# Step 9: Runnable Runtime Prototype (CLI)

## Why this step

This step makes the project directly runnable as a working prototype, not only module code.

## What was implemented

- CLI runtime in `src/app/cli.py` with command-driven execution.
- Secure transaction listing support in `src/database/transaction_store.py`.
- Basic CLI smoke test in `tests/unit/test_cli_basic.py`.

## CLI commands

Use:

```bash
python -m src.app.cli --db data/ruralshield.db <command>
```

Commands:
- `init-db`
- `add-user --user-id ... --phone ... --pin ...`
- `add-tx --user-id ... --pin ... --amount ... --recipient ...`
- `list-tx --user-id ... --pin ... --limit 10`
- `sync --server-url http://localhost:8000`
- `audit-check`

## Example end-to-end demo flow

```bash
python -m src.app.cli --db data/ruralshield.db init-db
python -m src.app.cli --db data/ruralshield.db add-user --user-id u1 --phone +919999999999 --pin 1234
python -m src.app.cli --db data/ruralshield.db add-tx --user-id u1 --pin 1234 --amount 1850 --recipient "Local Merchant"
python -m src.app.cli --db data/ruralshield.db list-tx --user-id u1 --pin 1234
python -m src.app.cli --db data/ruralshield.db audit-check
```

## Notes

- If `add-tx` fails with `ModuleNotFoundError: cryptography`, install project dependencies in a virtual environment.
- Runtime now supports a clear demonstration of offline secure flow plus visible progress output.
