# Implementation

## Project Setup Steps
### Local setup
1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies using `requirements.txt`.
4. Configure environment variables if required.
5. Run locally using FastAPI or Docker.

### Docker setup
The project supports Docker-based execution for local parity with deployment.

### Deployment setup
The final version is hosted on Render using a Docker-driven workflow and PostgreSQL for server-side persistence.

## Code Structure (Folder Explanation)
### `src/ui/`
Contains customer and bank/admin routes, page templates, and static assets.

### `src/server/`
Contains central backend application code, database models, authentication logic, and API routes.

### `src/deploy/`
Contains the combined deployment entrypoint used on Render.

### `data/`
Contains local demo state and import/export data used in the project flow.

### `docs/`
Contains project documentation, progress logs, architecture notes, deployment guides, and the Wiki report pack.

### `tests/`
Contains checks for critical modules and end-to-end reliability.

## Key Code Snippets (with Explanation)
### Example 1: Fraud decision structure
The fraud engine does not only return a score. It returns a complete decision object including reasons. This is important because the project emphasizes explainability.

```python
{
  "risk_score": 75,
  "decision": "HELD",
  "reasons": ["NEW_DEVICE", "HIGH_AMOUNT"]
}
```

**Why this matters:**
This makes the fraud engine useful not only for automation, but also for bank review, reporting, and customer feedback.

### Example 2: Sync-first local preservation concept
The project uses a local-first queue so user intent is not lost.

```text
create transaction -> save locally -> mark pending -> sync later -> acknowledge centrally
```

**Why this matters:**
This ensures continuity in poor network environments.

## Integration Details
The project integrates several layers:
- customer UI to backend routes,
- fraud engine to transaction flow,
- local SQLite state to sync queue,
- central PostgreSQL to admin analytics,
- deployed public UI to API docs and health endpoints.

## Comparison with Real Banking Systems
A real banking backend would usually involve stronger external integrations and central transaction rails, but the structure here is conceptually similar in important ways:
- role separation
- centralized monitoring
- staged transaction handling
- risk interpretation
- operational admin controls

## Repository Link
Repository Link: https://github.com/bhumishah01/CyberShakti-Banking-Framework

## Implementation Strength
The implementation is stronger than a basic classroom prototype because it includes not only backend logic, but real deployment, multiple user roles, analytics, safety features, and documentation support.

## Navigation
- Previous: [[Methodology]]
- Next: [[Results]]
