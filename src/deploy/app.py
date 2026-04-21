"""
Deployment entrypoint for Render (single web service).

Why this exists:
- Locally we often run 3 containers (ui + api + postgres) via docker-compose.
- For Render "one live URL", it's simpler to run UI + API in a single ASGI app:
  - UI mounted at `/`
  - Server API mounted at `/api`

This keeps the demo full-stack and avoids CORS issues (same origin).
"""

from __future__ import annotations

from fastapi import FastAPI

from src.server.app import app as api_app
from src.ui.app import app as ui_app


app = FastAPI(title="RuralShield (UI + API)")

# Health check used by Render.
@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "ruralshield-ui-api"}


# Mount API first to reserve /api/* namespace.
app.mount("/api", api_app)

# UI is the primary experience.
app.mount("/", ui_app)

