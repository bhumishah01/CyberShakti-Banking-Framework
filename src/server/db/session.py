from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.server.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine():
    # Lazy-init so importing server modules doesn't immediately require env vars.
    # If DATABASE_URL is missing, this will still fail when first used (by design).
    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_sessionmaker():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def get_db():
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()
