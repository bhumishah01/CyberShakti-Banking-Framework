from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Server
    app_name: str = "RuralShield Server API"
    environment: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000

    # Auth/JWT
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_minutes: int = 60 * 12

    # Postgres
    database_url: str  # e.g. postgresql+psycopg://user:pass@db:5432/ruralshield

    # Field encryption (server-side at-rest protection for sensitive fields)
    field_enc_key: str  # 32+ chars; used to derive AES-GCM key

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        """
        Render/Heroku-style Postgres URLs often come as:
          - postgres://...
          - postgresql://...

        SQLAlchemy defaults those to psycopg2 unless a driver is specified.
        We use psycopg (v3), so normalize to `postgresql+psycopg://...`.
        """
        url = (v or "").strip()
        if not url:
            return url

        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url[len("postgres://") :]
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url[len("postgresql://") :]

        # If someone configured the old psycopg2 driver explicitly, switch to psycopg (v3).
        url = url.replace("postgresql+psycopg2://", "postgresql+psycopg://")
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Lazy-load settings so importing modules doesn't crash tooling.
    # FastAPI will still fail fast on startup if required env vars are missing.
    return Settings()
