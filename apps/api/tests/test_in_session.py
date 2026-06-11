"""In-Session backend: set logging (idempotent), session pre-fill, PR detection."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from obelisk_api.tools.deterministic import compute_1rm
from tests.conftest import JOSH_PROFILE, FakeAnthropic, draft_then_explain

pytestmark = pytest.mark.integration

Client = tuple[TestClient, Callable[[str], None]]


def _create_profile(c: TestClient) -> dict:
    resp = c.post("/v1/athlete/profile", json=JOSH_PROFILE)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _create_block(c: TestClient, fake: FakeAnthropic) -> dict:
    fake.queue(*draft_then_explain())
    resp = c.post("/v1/blocks", json={"name": "Crucible-25", "goal": "aerobic base + strength"})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _first_weekday_on_or_after(start: date, weekday: int) -> date:
    """First date >= start whose weekday() == weekday (Mon=0)."""
    return start + timedelta(days=(weekday - start.weekday()) % 7)


def _set_payload(**over) -> dict:
    base = {
        "client_id": str(uuid.uuid4()),
        "session_date": date.today().isoformat(),
        "exercise": "Back Squat — main",
        "lift_key": "back_squat",
        "set_index": 1,
        "weight_lb": 185.0,
        "reps": 5,
        "rpe": 8.0,
        "completed": True,
    }
    base.update(over)
    return base


# --- Auth ------------------------------------------------------------------
def test_log_requires_auth(raw_client: TestClient) -> None:
    assert raw_client.post("/v1/log", json={"sets": [_set_payload()]}).status_code == 401


# --- Idempotent batch ingest ----------------------------------------------
def test_post_log_is_idempotent_on_client_id(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    sets = [_set_payload(set_index=i) for i in range(1, 4)]

    first = c.post("/v1/log", json={"sets": sets})
    assert first.status_code == 201, first.text
    assert first.json() == {"received": 3, "inserted": 3, "duplicates": 0}

    # Replaying the exact same batch (gym-basement reconnect) inserts nothing new.
    replay = c.post("/v1/log", json={"sets": sets})
    assert replay.json() == {"received": 3, "inserted": 0, "duplicates": 3}

    feed = c.get("/v1/log", params={"type": "set"}).json()
    assert feed["total"] == 3
    assert len(feed["entries"]) == 3
    assert {e["type"] for e in feed["entries"]} == {"set"}


def test_post_log_dedupes_within_a_single_batch(client: Client) -> None:
    c, _ = client
    _create_profile(c)
    cid = str(uuid.uuid4())
    sets = [_set_payload(client_id=cid), _set_payload(client_id=cid, weight_lb=999)]
    resp = c.post("/v1/log", json={"sets": sets}).json()
    assert resp == {"received": 2, "inserted": 1, "duplicates": 1}


def test_log_404_without_profile(client: Client) -> None:
    c, _ = client
    assert c.post("/v1/log", json={"sets": [_set_payload()]}).status_code == 404


# --- Session prescription + pre-fill --------------------------------------
def test_session_prescribes_monday_with_squat_main(
    client: Client, fake_anthropic: FakeAnthropic
) -> None:
    c, _ = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    start = date.fromisoformat(block["start_date"])
    monday = _first_weekday_on_or_after(start, 0)  # Strength A

    resp = c.get(f"/v1/blocks/{block['id']}/sessions/{monday.isoformat()}")
    assert resp.status_code == 200, resp.text
    session = resp.json()
    assert session["day"] == "Mon"
    assert session["session_title"] == "Strength A"
    assert session["is_rest_day"] is False

    squat = next(e for e in session["exercises"] if e["lift_key"] == "back_squat")
    assert squat["kind"] == "main"
    assert squat["rest_default_sec"] == 180  # compound default
    # Week-1 5s wave at TM=220: 65/75/85%.
    assert [s["weight_lb"] for s in squat["sets"]] == [145, 165, 185]
    assert squat["sets"][-1]["amrap"] is True
    assert squat["prior_sets"] == []  # nothing logged yet


def test_monday_set_prefills_next_monday(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    start = date.fromisoformat(block["start_date"])
    monday_w1 = _first_weekday_on_or_after(start, 0)
    monday_w2 = monday_w1 + timedelta(days=7)

    # Log three squat sets on week-1 Monday.
    logged = [
        _set_payload(
            client_id=str(uuid.uuid4()),
            session_date=monday_w1.isoformat(),
            set_index=i,
            weight_lb=190.0 + i * 5,
            reps=5,
            occurred_at=datetime.combine(monday_w1, datetime.min.time()).isoformat() + "+00:00",
        )
        for i in range(1, 4)
    ]
    assert c.post("/v1/log", json={"sets": logged}).status_code == 201

    # Next Monday's session pre-fills the squat exercise with last Monday's actuals.
    session = c.get(f"/v1/blocks/{block['id']}/sessions/{monday_w2.isoformat()}").json()
    squat = next(e for e in session["exercises"] if e["lift_key"] == "back_squat")
    prior = squat["prior_sets"]
    assert [p["set_index"] for p in prior] == [1, 2, 3]
    assert [p["weight_lb"] for p in prior] == [195.0, 200.0, 205.0]


def test_session_sunday_is_note_only(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    start = date.fromisoformat(block["start_date"])
    sunday = _first_weekday_on_or_after(start, 6)
    session = c.get(f"/v1/blocks/{block['id']}/sessions/{sunday.isoformat()}").json()
    assert session["session_title"] == "Rest"
    assert all(e["kind"] == "note" for e in session["exercises"])
    assert all(e["sets"] == [] for e in session["exercises"])


def test_session_404_for_foreign_block(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, set_user = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    set_user("intruder")
    _create_profile(c)
    resp = c.get(f"/v1/blocks/{block['id']}/sessions/{date.today().isoformat()}")
    assert resp.status_code == 404


# --- PR / e1RM -------------------------------------------------------------
def test_pr_falls_back_to_profile_then_logged(client: Client) -> None:
    c, _ = client
    _create_profile(c)

    # No logs yet → profile baseline (JOSH back_squat = 259).
    pr = c.get("/v1/athlete/pr/back_squat").json()
    assert pr == {
        "lift": "back_squat",
        "e1rm": 259,
        "source": "profile",
        "weight_lb": None,
        "reps": None,
        "occurred_at": None,
    }

    # Log a set that out-estimates the baseline → logged source wins.
    c.post("/v1/log", json={"sets": [_set_payload(weight_lb=245.0, reps=3)]})
    pr = c.get("/v1/athlete/pr/back_squat").json()
    assert pr["source"] == "logged"
    assert pr["e1rm"] == compute_1rm(245.0, 3)
    assert pr["weight_lb"] == 245.0


def test_pr_none_for_untested_lift(client: Client) -> None:
    c, _ = client
    _create_profile(c)
    pr = c.get("/v1/athlete/pr/trap_bar_deadlift").json()
    assert pr == {
        "lift": "trap_bar_deadlift",
        "e1rm": None,
        "source": "none",
        "weight_lb": None,
        "reps": None,
        "occurred_at": None,
    }


# --- Analytics -------------------------------------------------------------
def test_lift_analytics_best_e1rm_per_day(client: Client) -> None:
    c, _ = client
    _create_profile(c)
    d1, d2 = "2026-05-01", "2026-05-08"
    c.post(
        "/v1/log",
        json={
            "sets": [
                # Day 1: two squat sets — the heavier one wins the day.
                _set_payload(client_id=str(uuid.uuid4()), session_date=d1, weight_lb=185.0, reps=5),
                _set_payload(client_id=str(uuid.uuid4()), session_date=d1, weight_lb=205.0, reps=3),
                # Day 2: one squat set.
                _set_payload(client_id=str(uuid.uuid4()), session_date=d2, weight_lb=215.0, reps=3),
            ]
        },
    )
    series = c.get("/v1/athlete/analytics/lifts").json()["series"]
    squat = series["back_squat"]
    assert [p["date"] for p in squat] == [d1, d2]
    assert squat[0]["e1rm"] == compute_1rm(205.0, 3)  # heavier set wins day 1
    assert squat[1]["e1rm"] == compute_1rm(215.0, 3)
