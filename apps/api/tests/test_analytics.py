"""PostHog analytics wrapper: gated no-op + pass-through, never raises."""

from __future__ import annotations

from typing import Any

import pytest

from obelisk_api.config import get_settings
from obelisk_api.services import analytics


@pytest.fixture(autouse=True)
def _reset() -> Any:
    analytics.reset_for_tests()
    yield
    analytics.reset_for_tests()
    get_settings.cache_clear()


def test_capture_is_noop_without_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTHOG_API_KEY", raising=False)
    get_settings.cache_clear()
    analytics.reset_for_tests()
    # Must not raise even though nothing is configured.
    analytics.capture("user-1", "set_logged", {"count": 3})


def test_capture_passes_through_to_client(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    class FakeClient:
        def capture(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    monkeypatch.setattr(analytics, "_client", FakeClient())
    monkeypatch.setattr(analytics, "_initialized", True)

    analytics.capture("user-1", "block_created", {"program_model": "hybrid_531"})
    assert len(calls) == 1
    assert calls[0]["distinct_id"] == "user-1"
    assert calls[0]["event"] == "block_created"
    assert calls[0]["properties"]["program_model"] == "hybrid_531"


def test_capture_swallows_client_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class Boom:
        def capture(self, **kwargs: Any) -> None:
            raise RuntimeError("posthog down")

    monkeypatch.setattr(analytics, "_client", Boom())
    monkeypatch.setattr(analytics, "_initialized", True)
    # Best-effort: a failing analytics backend never propagates.
    analytics.capture("user-1", "set_logged")
