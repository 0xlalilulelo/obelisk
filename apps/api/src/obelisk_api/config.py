"""Application settings, loaded from the environment (pydantic-settings).

One source of truth for config. Secrets come from .env locally and Doppler in
shared envs; nothing is hardcoded.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# The repo-root .env is the single source of truth (matches the README). Resolved
# absolutely so it loads regardless of CWD; pydantic ignores it if absent (e.g. in
# Docker, where env vars are injected directly).
_ROOT_ENV = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(_ROOT_ENV), ".env"), extra="ignore", case_sensitive=False
    )

    # --- LLM ---
    anthropic_api_key: str = ""
    obelisk_model: str = "claude-sonnet-4-6"
    # Hard per-session USD ceiling passed to the agent loop.
    max_cost_usd: float = 1.50

    # --- Database ---
    database_url: str = "postgresql+psycopg://obelisk:obelisk@localhost:5432/obelisk"

    # --- Auth: Clerk ---
    clerk_issuer: str = ""
    clerk_audience: str | None = None
    clerk_secret_key: str = ""

    # --- Object storage ---
    obelisk_s3_bucket: str = "obelisk-artifacts"
    obelisk_s3_region: str = "auto"
    obelisk_s3_endpoint: str | None = None

    # --- Observability ---
    sentry_dsn: str = ""
    environment: str = "development"

    # --- Rate limiting (slowapi; PRD security checklist) ---
    rate_limit_enabled: bool = True

    # --- CORS (desktop dev server + Tauri origin) ---
    cors_origins: list[str] = [
        "http://localhost:1420",
        "http://localhost:5173",
        "tauri://localhost",
        "https://tauri.localhost",
    ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
