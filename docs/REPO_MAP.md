# Repository Map (Quick Navigation)

Use this file to quickly locate any part of the project.

## Core Docs
- Foundation lock: `docs/STEPWISE PROGRESS/STEP_01_FOUNDATION.md`
- Step 2 auth and keys: `docs/STEPWISE PROGRESS/STEP_02_AUTH_AND_KEYS.md`
- Step 3 encrypted storage pipeline: `docs/STEPWISE PROGRESS/STEP_03_ENCRYPTED_TRANSACTION_PIPELINE.md`
- Step 4 fraud rule engine: `docs/STEPWISE PROGRESS/STEP_04_FRAUD_RULE_ENGINE.md`
- Step 5 sync manager: `docs/STEPWISE PROGRESS/STEP_05_SYNC_MANAGER.md`
- Architecture: `docs/ARCHITECTURE.md`
- Threat model: `docs/THREAT_MODEL.md`
- Roadmap: `docs/ROADMAP.md`
- Full blueprint + JSON: `docs/PROJECT_BLUEPRINT.md`

## Source Code
- Authentication: `src/auth/service.py`
- Cryptography: `src/crypto/service.py`
- Database init/schema: `src/database/init_db.py`
- Secure transaction store: `src/database/transaction_store.py`
- Fraud engine: `src/fraud/engine.py`
- Sync manager: `src/sync/manager.py`
- Audit chain (upcoming): `src/audit/chain.py`

## Tests
- DB init test: `tests/unit/test_init_db.py`
- Auth tests: `tests/unit/test_auth_service.py`
- Fraud rules tests: `tests/unit/test_fraud_engine.py`
- Secure transaction tests: `tests/unit/test_transaction_store.py`
- Sync manager tests: `tests/unit/test_sync_manager.py`

## Progress Tracking
- Current branch: `main`
- Commit style: `type(scope): summary`
- One meaningful commit per completed unit
