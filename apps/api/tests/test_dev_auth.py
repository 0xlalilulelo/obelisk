"""Dev-auth escape hatch: only active when configured and not in production."""

from __future__ import annotations

import pytest

from obelisk_api.auth.clerk import _dev_claims_or_none
from obelisk_api.config import get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    yield
    get_settings.cache_clear()


def test_dev_token_grants_synthetic_claims(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_AUTH_TOKEN", "tok123")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    claims = _dev_claims_or_none("tok123")
    assert claims is not None
    assert claims["sub"] == "dev_user"


def test_wrong_token_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_AUTH_TOKEN", "tok123")
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    assert _dev_claims_or_none("nope") is None


def test_disabled_without_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEV_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()
    assert _dev_claims_or_none("anything") is None


def test_disabled_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEV_AUTH_TOKEN", "tok123")
    monkeypatch.setenv("ENVIRONMENT", "production")
    get_settings.cache_clear()
    assert _dev_claims_or_none("tok123") is None
