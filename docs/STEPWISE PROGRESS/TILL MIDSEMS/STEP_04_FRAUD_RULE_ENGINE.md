# Step 4: Fraud Rule Engine and Explainable Risk Scoring

## What was implemented

- Rule-based fraud scoring engine in `src/fraud/engine.py`.
- Automatic fraud scoring integrated in `src/database/transaction_store.py`.
- Reason-code based explainability for risk decisions.

## Rules implemented

- `HIGH_AMOUNT`: amount >= 3000.
- `NEW_RECIPIENT`: recipient not found in user history.
- `ODD_HOUR`: transaction hour before 06:00 or from 22:00 onward.
- `RAPID_BURST`: 3 or more recent transactions within 10 minutes.
- `AUTH_FAILURES`: recent failed attempts >= 3.

## Risk outputs

- `risk_score`: 0 to 100 (capped at 100).
- `risk_level`: LOW / MEDIUM / HIGH.
- `reason_codes`: list of trigger reasons (explainable alert basis).

## Integration changes

- `create_secure_transaction` now computes risk automatically from local history and auth state.
- `StoredTransaction` now returns `risk_score`, `risk_level`, and `reason_codes`.
- Outbox packet now carries `reason_codes` for explainable sync-side review.

## Tests added

- `tests/unit/test_fraud_engine.py`:
  - new recipient low-risk case,
  - high-risk combined triggers case.
- `tests/unit/test_transaction_store.py`:
  - verifies computed risk metadata is returned,
  - existing tamper-detection path remains valid.

Result: `8 passed`.
