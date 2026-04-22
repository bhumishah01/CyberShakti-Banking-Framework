# Implementation

## Project Setup Steps
1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies from `requirements.txt`.
4. Configure required environment variables if needed.
5. Run the application locally using FastAPI or Docker.
6. Deploy the project using Render for live hosting.

## Code Structure (Folder Explanation)
### `src/ui/`
Customer and bank/admin templates, route bindings, and static assets.

### `src/server/`
Backend APIs, database models, authentication logic, and central server functionality.

### `src/deploy/`
Combined deployment entrypoint used for the live Render app.

### `data/`
Local demo data, imports, exports, and offline persistence files.

### `docs/`
Architecture, deployment, progress logs, and report files.

### `tests/`
Automated checks for important system behavior.

## Key Code Snippets (with Explanation)
### Fraud decision object
```python
{
  "risk_score": 75,
  "decision": "HELD",
  "reasons": ["NEW_DEVICE", "HIGH_AMOUNT"]
}
```
This matters because the system does not only classify a transaction; it explains the classification.

### Local-first sync concept
```text
create transaction -> save locally -> mark pending -> sync later -> central acknowledgement
```
This matters because the system preserves user intent under low-connectivity conditions.

## Integration Details
- customer UI connects to backend route logic
- fraud engine connects to transaction creation
- SQLite connects to the sync queue
- PostgreSQL supports the deployed central system
- admin analytics depend on monitored transaction and risk data

## Repository Link
Repository Link: https://github.com/bhumishah01/CyberShakti-Banking-Framework

## Navigation
- Previous: [[Methodology]]
- Next: [[Results]]
