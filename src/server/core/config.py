from __future__ import annotations

from functools import lru_cache

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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Lazy-load settings so importing modules doesn't crash tooling.
    # FastAPI will still fail fast on startup if required env vars are missing.
    return Settings()
