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
- Step 9 runtime prototype: `docs/STEPWISE PROGRESS/STEP_09_RUNTIME_PROTOTYPE.md`
- Step 10 web interface: `docs/STEPWISE PROGRESS/STEP_10_WEB_INTERFACE.md`
- Step 11 product demo upgrade: `docs/STEPWISE PROGRESS/STEP_11_PRODUCT_DEMO_UPGRADE.md`
- Step 12 scam intervention engine: `docs/STEPWISE PROGRESS/STEP_12_SCAM_INTERVENTION_ENGINE.md`
- Step 13 trusted safety controls: `docs/STEPWISE PROGRESS/STEP_13_TRUSTED_SAFETY_CONTROLS.md`
- Step 14 local language and usability: `docs/STEPWISE PROGRESS/STEP_14_LOCAL_LANGUAGE_AND_USABILITY.md`
- Step 15 fraud scenario simulator: `docs/STEPWISE PROGRESS/STEP_15_FRAUD_SCENARIO_SIMULATOR.md`
- Step 16 agent voice and impact report: `docs/STEPWISE PROGRESS/STEP_16_AGENT_VOICE_AND_IMPACT_REPORT.md`
- Step 17 professor demo walkthrough: `docs/STEPWISE PROGRESS/STEP_17_PROFESSOR_DEMO_WALKTHROUGH.md`
- Step 18 change log export: `docs/STEPWISE PROGRESS/STEP_18_CHANGE_LOG_EXPORT.md`
- Step 19 full multilingual UI: `docs/STEPWISE PROGRESS/STEP_19_FULL_I18N_UI.md`
- Step 20 sync queue + night sync simulator: `docs/STEPWISE PROGRESS/STEP_20_SYNC_QUEUE_AND_NIGHT_SYNC.md`
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
- Change log capture: `src/audit/change_log.py`
- Backend API: `src/backend/app.py`
- Evaluation simulation: `src/evaluation/simulation.py`
- CLI runtime prototype: `src/app/cli.py`
- Web UI app: `src/ui/app.py`
- Web UI templates: `src/ui/templates/`
- Agent UI: `src/ui/templates/agent.html`
- Impact report UI: `src/ui/templates/impact_report.html`
- Demo walkthrough UI: `src/ui/templates/demo_walkthrough.html`
- Web UI styles: `src/ui/static/styles.css`

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
- CLI smoke test: `tests/unit/test_cli_basic.py`
- Web UI tests: `tests/unit/test_ui_app.py`

## Scripts and Reports
- Metrics generator: `scripts/generate_metrics.py`
- Metrics JSON output: `reports/metrics/step8_metrics.json`
- Metrics summary output: `reports/metrics/step8_metrics_summary.md`
- Demo/task shortcuts: `Makefile`

## Progress Tracking
- Current branch: `main`
- Commit style: `type(scope): summary`
- One meaningful commit per completed unit
