# Repository Map (Quick Navigation)

Use this file to quickly locate any part of the project.

## Core Docs
- Foundation lock: `docs/STEPWISE PROGRESS/STEP_01_FOUNDATION.md`
- Step 2 auth and keys: `docs/STEPWISE PROGRESS/STEP_02_AUTH_AND_KEYS.md`
- Step 3 encrypted storage pipeline: `docs/STEPWISE PROGRESS/STEP_03_ENCRYPTED_TRANSACTION_PIPELINE.md`
- Step 4 fraud rule engine: `docs/STEPWISE PROGRESS/STEP_04_FRAUD_RULE_ENGINE.md`
- Step 5 sync manager: `docs/STEPWISE PROGRESS/STEP_05_SYNC_MANAGER.md`
- Step 6 audit chain: `docs/STEPWISE PROGRESS/STEP_06_AUDIT_CHAIN.md`
- Step 7 minimal backend: `docs/STEPWISE PROGRESS/STEP_07_MINIMAL_BACKEND.md`
- Step 8 evaluation and demo: `docs/STEPWISE PROGRESS/STEP_08_EVALUATION_AND_DEMO.md`
- Architecture: `docs/ARCHITECTURE.md`
- Threat model: `docs/THREAT_MODEL.md`
- Roadmap: `docs/ROADMAP.md`
- Demo runbook: `docs/DEMO_RUNBOOK.md`
- Full blueprint + JSON: `docs/PROJECT_BLUEPRINT.md`

## Source Code
- Authentication: `src/auth/service.py`
- Cryptography: `src/crypto/service.py`
- Database init/schema: `src/database/init_db.py`
- Secure transaction store: `src/database/transaction_store.py`
- Fraud engine: `src/fraud/engine.py`
- Sync manager: `src/sync/manager.py`
- Sync HTTP client: `src/sync/client.py`
- Audit chain: `src/audit/chain.py`
- Backend API: `src/backend/app.py`
- Evaluation simulation: `src/evaluation/simulation.py`

## Tests
- DB init test: `tests/unit/test_init_db.py`
- Auth tests: `tests/unit/test_auth_service.py`
- Fraud rules tests: `tests/unit/test_fraud_engine.py`
- Secure transaction tests: `tests/unit/test_transaction_store.py`
- Sync manager tests: `tests/unit/test_sync_manager.py`
- Audit chain tests: `tests/unit/test_audit_chain.py`
- Backend API tests: `tests/unit/test_backend_api.py`
- Sync client tests: `tests/unit/test_sync_client.py`
- Evaluation tests: `tests/unit/test_simulation.py`

## Scripts and Reports
- Metrics generator: `scripts/generate_metrics.py`
- Metrics JSON output: `reports/metrics/step8_metrics.json`
- Metrics summary output: `reports/metrics/step8_metrics_summary.md`

## Progress Tracking
- Current branch: `main`
- Commit style: `type(scope): summary`
- One meaningful commit per completed unit
