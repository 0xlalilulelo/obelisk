"""Push: quiet-hours / anti-spam policy, content, gated send, and prefs endpoints."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from obelisk_api.config import get_settings
from obelisk_api.services import push
from tests.conftest import JOSH_PROFILE

Client = tuple[TestClient, Callable[[str], None]]


# --- Quiet hours -----------------------------------------------------------
def test_quiet_hours_wraps_midnight() -> None:
    assert push.in_quiet_hours("23:00", "22:00", "06:00")
    assert push.in_quiet_hours("05:59", "22:00", "06:00")
    assert not push.in_quiet_hours("06:00", "22:00", "06:00")  # end exclusive
    assert not push.in_quiet_hours("12:00", "22:00", "06:00")


def test_quiet_hours_same_day_window() -> None:
    assert push.in_quiet_hours("12:00", "09:00", "17:00")
    assert not push.in_quiet_hours("08:00", "09:00", "17:00")


# --- Anti-spam policy ------------------------------------------------------
def _now() -> datetime:
    return datetime(2026, 6, 9, 7, 0, tzinfo=UTC)


def test_should_send_first_morning() -> None:
    assert push.should_send_morning(
        enabled=True,
        now_hhmm="07:00",
        quiet_start="22:00",
        quiet_end="06:00",
        last_sent=None,
        last_opened=None,
        now=_now(),
    )


def test_respects_disabled_and_quiet_hours() -> None:
    base = dict(
        now_hhmm="07:00",
        quiet_start="22:00",
        quiet_end="06:00",
        last_sent=None,
        last_opened=None,
        now=_now(),
    )
    assert not push.should_send_morning(enabled=False, **base)  # type: ignore[arg-type]
    assert not push.should_send_morning(
        enabled=True,
        now_hhmm="05:00",
        quiet_start="22:00",
        quiet_end="06:00",
        last_sent=None,
        last_opened=None,
        now=_now(),
    )


def test_one_per_day_and_defer_if_unopened() -> None:
    now = _now()
    # Already sent today → no.
    assert not push.should_send_morning(
        enabled=True,
        now_hhmm="07:00",
        quiet_start="22:00",
        quiet_end="06:00",
        last_sent=now - timedelta(hours=2),
        last_opened=None,
        now=now,
    )
    # Yesterday but unopened and <24h → defer.
    assert not push.should_send_morning(
        enabled=True,
        now_hhmm="07:00",
        quiet_start="22:00",
        quiet_end="06:00",
        last_sent=now - timedelta(hours=20),
        last_opened=None,
        now=now,
    )
    # Yesterday and opened → send.
    assert push.should_send_morning(
        enabled=True,
        now_hhmm="07:00",
        quiet_start="22:00",
        quiet_end="06:00",
        last_sent=now - timedelta(hours=20),
        last_opened=now - timedelta(hours=19),
        now=now,
    )


# --- Content ---------------------------------------------------------------
def test_morning_content_ties_to_a_number() -> None:
    title, body = push.morning_ping_content("Strength A", 82, "Resting HR back to baseline.")
    assert title == "Today: Strength A"
    assert "Readiness 82." in body
    assert "Resting HR" in body


def test_weekly_recap_content() -> None:
    title, body = push.weekly_recap_content(4, 5, "Squat PR 245", "Strength A")
    assert "4/5" in title
    assert "Squat PR 245" in body
    assert "Strength A" in body


# --- Gated send ------------------------------------------------------------
def test_send_push_is_noop_without_apns(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("APNS_KEY_ID", "APNS_TEAM_ID", "APNS_PRIVATE_KEY"):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    try:
        assert asyncio.run(push.send_push("token", "t", "b")) is False
    finally:
        get_settings.cache_clear()


# --- Endpoints -------------------------------------------------------------
def test_register_and_update_preferences(client: Client) -> None:
    c, _ = client
    c.post("/v1/athlete/profile", json=JOSH_PROFILE)

    reg = c.post("/v1/notifications/register", json={"device_token": "abc123"})
    assert reg.status_code == 201, reg.text
    body = reg.json()
    assert body["device_registered"] is True
    assert "abc123" not in str(body)  # token never echoed
    assert body["morning_ping_enabled"] is True

    patched = c.patch(
        "/v1/notifications/preferences",
        json={"morning_ping_time": "06:30", "weekly_recap_enabled": False},
    ).json()
    assert patched["morning_ping_time"] == "06:30"
    assert patched["weekly_recap_enabled"] is False
    assert patched["device_registered"] is True  # unchanged


def test_preferences_reject_bad_time(client: Client) -> None:
    c, _ = client
    c.post("/v1/athlete/profile", json=JOSH_PROFILE)
    resp = c.patch("/v1/notifications/preferences", json={"morning_ping_time": "25:00"})
    assert resp.status_code == 422


def test_notifications_require_auth(raw_client: TestClient) -> None:
    assert raw_client.get("/v1/notifications/preferences").status_code == 401
