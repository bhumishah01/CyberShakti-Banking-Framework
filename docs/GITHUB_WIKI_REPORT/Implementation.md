# Implementation

## Project Setup Steps
### Local development
1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies from `requirements.txt`.
4. Run the FastAPI application locally or use Docker.

### Docker-based local setup
The project supports `docker compose up --build`, which starts the local stack and reflects the same deployment structure used on Render.

### Live deployment
The final application is deployed on Render using Docker, with PostgreSQL as the central server-side database.

## Code Structure (Folder Explanation)
- `src/ui/`
  Contains the customer portal, bank/admin portal, templates, and static files.
- `src/server/`
  Contains the server-side application logic, database access, authentication handling, and APIs.
- `src/deploy/`
  Contains the combined deployment entrypoint used for live hosting.
- `data/`
  Holds local/demo storage and exported artifacts.
- `docs/`
  Contains architecture, deployment, stepwise progress, and report support documentation.
- `tests/`
  Contains unit and integration-level checks for major modules.

## Key Code Areas
### UI Layer
The UI was built using FastAPI + Jinja templates so that both presentation and routing remain in one understandable stack. This also helped keep deployment simple.

### Fraud Logic
The fraud engine integrates rule-based detection with behavior-aware scoring. Instead of just returning a number, it stores reasons so that downstream pages can explain the decision.

### Sync Engine
The sync logic was implemented with explicit statuses and queue semantics. This made it possible to build pages like Sync Queue, selective sync, and held/release workflows in the bank portal.

### Admin Analytics
Analytics are generated from locally available and synchronized data to produce trend views, reason summaries, and user-wise risk breakdowns.

## Integration Details
The project was implemented as a full-stack application where UI and backend are closely integrated:
- the customer and admin pages call backend routes and APIs,
- authentication state is reused across flows,
- data moves from local SQLite to central PostgreSQL through a controlled sync process.

## Repository Link
Repository Link: https://github.com/bhumishah01/CyberShakti-Banking-Framework
