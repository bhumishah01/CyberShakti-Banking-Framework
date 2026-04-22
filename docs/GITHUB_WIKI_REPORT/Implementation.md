# Implementation

## Project Setup Steps
1. Clone the repository.
2. Create and activate a Python virtual environment if running locally.
3. Install dependencies from `requirements.txt`.
4. Configure environment variables where needed.
5. Run locally using FastAPI or Docker Compose.
6. Deploy using Render.

## Code Structure
### `src/ui/`
Contains the main UI controller, templates, and static assets.

### `src/server/`
Contains the central FastAPI API, models, routers, services, and server configuration.

### `src/auth/`
Contains local authentication and biometric hash support.

### `src/fraud/`
Contains the local fraud engine.

### `src/database/`
Contains local SQLite initialization, transaction storage, device/profile/monitoring stores.

### `src/sync/`
Contains sync manager and client logic.

### `src/deploy/`
Contains the combined mounted app used for live deployment.

### `docs/`
Contains project documentation, report content, wiki content, and system reference files.

## Key Code Snippets
### Example fraud decision object
```python
{
  "risk_score": 75,
  "decision": "HELD",
  "reasons": ["NEW_DEVICE", "HIGH_AMOUNT"]
}
```
This shows that the project stores not just a score, but an explainable decision payload.

### Example sync states
```python
PENDING -> RETRYING -> SYNCED
```
This demonstrates the operational state transitions of the offline-first outbox.

## Integration Details
- Customer UI uses local SQLite and selective AJAX endpoints.
- Admin UI uses local analytics helpers plus optional central API data.
- Render deployment mounts UI at `/` and API at `/api`.

## Repository Link
Repository Link: [https://github.com/bhumishah01/CyberShakti-Banking-Framework](https://github.com/bhumishah01/CyberShakti-Banking-Framework)

## Navigation
- Previous: [[Methodology]]
- Next: [[Results]]
