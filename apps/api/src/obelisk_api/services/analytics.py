"""Server-side product analytics (PostHog, PRD §2.8).

A thin, fail-safe wrapper: a no-op when no key is configured, and any SDK error is
swallowed — analytics must never break a request. Only ``user_id`` is sent as the
distinct id; event properties must never carry PII (security checklist).
"""

from __future__ import annotations

import contextlib
from typing import Any

from obelisk_api.config import get_settings

_client: Any = None
_initialized = False


def _get_client() -> Any:
    global _client, _initialized
    if _initialized:
        return _client
    _initialized = True
    settings = get_settings()
    if settings.posthog_api_key:
        from posthog import Posthog

        _client = Posthog(settings.posthog_api_key, host=settings.posthog_host)
    return _client


def capture(distinct_id: str, event: str, properties: dict[str, Any] | None = None) -> None:
    """Record a product event. No-op when PostHog isn't configured."""
    client = _get_client()
    if client is None:
        return
    # Analytics is best-effort; a failing backend must never break a request.
    with contextlib.suppress(Exception):
        client.capture(distinct_id=distinct_id, event=event, properties=properties or {})


def reset_for_tests() -> None:
    """Clear the cached client so a test can reconfigure the key."""
    global _client, _initialized
    _client = None
    _initialized = False
