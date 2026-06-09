"""Obelisk FastAPI application. All product routes are versioned under /v1."""

from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from obelisk_api.config import get_settings
from obelisk_api.routes import athlete, blocks, health


def _ensure_utf8_streams() -> None:
    """The migrated agent loop prints domain glyphs (× • → ≤). Force UTF-8 so a
    Windows cp1252 console can't crash a turn mid-flight."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def create_app() -> FastAPI:
    _ensure_utf8_streams()
    settings = get_settings()

    if settings.sentry_dsn:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,
        )

    app = FastAPI(
        title="Obelisk API",
        version="0.1.0",
        description="AI-native performance coaching — the Block Coach as a service.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    v1_prefix = "/v1"
    app.include_router(health.router, prefix=v1_prefix)
    app.include_router(athlete.router, prefix=v1_prefix)
    app.include_router(blocks.router, prefix=v1_prefix)

    return app


app = create_app()
