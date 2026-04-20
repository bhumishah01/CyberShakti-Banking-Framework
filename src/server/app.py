from __future__ import annotations

from fastapi import FastAPI

from src.server.core.config import get_settings
from src.server.db.base import Base
from src.server.db.session import get_engine
from src.server.routers import agent, auth, fraud, legacy, sync, transactions


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.0.0")

    # For this project, create tables automatically. In production you’d use Alembic migrations.
    Base.metadata.create_all(bind=get_engine())

    app.include_router(auth.router)
    app.include_router(transactions.router)
    app.include_router(sync.router)
    app.include_router(agent.router)
    app.include_router(fraud.router)
    app.include_router(legacy.router)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "ruralshield-server-api"}

    return app


app = create_app()
