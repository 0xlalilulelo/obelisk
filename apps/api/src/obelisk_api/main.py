"""Obelisk FastAPI application. All product routes are versioned under /v1."""

from __future__ import annotations

import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request

from obelisk_api.config import get_settings
from obelisk_api.ratelimit import limiter
from obelisk_api.routes import athlete, blocks, health, log, subscription, wearable


def _rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    detail = getattr(exc, "detail", "too many requests")
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {detail}"},
    )


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

    # Per-user rate limiting (slowapi). Disabled in unit tests via settings.
    limiter.enabled = settings.rate_limit_enabled
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)

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
    app.include_router(log.router, prefix=v1_prefix)
    app.include_router(wearable.router, prefix=v1_prefix)
    app.include_router(subscription.router, prefix=v1_prefix)
    app.include_router(subscription.webhook_router, prefix=v1_prefix)

    return app


app = create_app()
