# Demo Runbook

Use this runbook for project demonstration in class/viva.

## 1. Verify Project Health

```bash
pytest -q
```

Expected: all core tests pass (backend tests may skip if `fastapi` is not installed).

## 2. Generate Evaluation Metrics

```bash
python scripts/generate_metrics.py
```

Generated files:
- `reports/metrics/step8_metrics.json`
- `reports/metrics/step8_metrics_summary.md`

## 3. (Optional) Start Minimal Backend

```bash
uvicorn src.backend.app:app --host 0.0.0.0 --port 8000 --reload
```

Health check:
```bash
curl http://localhost:8000/health
```

## 4. Explain Core Security Flow

- PIN auth + lockout (`src/auth/service.py`)
- Encryption + signature (`src/crypto/service.py`)
- Offline secure storage (`src/database/transaction_store.py`)
- Fraud scoring (`src/fraud/engine.py`)
- Delayed sync + idempotency (`src/sync/manager.py`)
- Tamper-evident audit chain (`src/audit/chain.py`)

## 5. Show Stepwise Progress

Open folder:
- `docs/STEPWISE PROGRESS/`

Then walk through:
- Step 1 to Step 8 docs in order.

## 6. Show Outcome Claim

Use `reports/metrics/step8_metrics_summary.md` to present:
- Fraud reduction percentage
- True positive and false positive rates
- Low-latency local scoring
