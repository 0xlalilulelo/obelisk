"""HealthKit ingest (idempotent) + the readiness composite (pure + integration)."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import UTC, date, timedelta

import pytest
from fastapi.testclient import TestClient

from obelisk_api.services.readiness import (
    W_SLEEP,
    compute_readiness,
    hrv_score,
    rhr_score,
    sleep_score,
)
from tests.conftest import JOSH_PROFILE

pytestmark = pytest.mark.integration

Client = tuple[TestClient, Callable[[str], None]]
TARGET = date(2026, 6, 9)


def _create_profile(c: TestClient) -> None:
    assert c.post("/v1/athlete/profile", json=JOSH_PROFILE).status_code == 200


def _sleep(d: date, hours: float) -> dict:
    """A sleep sample the night before ``d`` (ends on the morning of ``d``)."""
    return {
        "sample_uuid": str(uuid.uuid4()),
        "sample_type": "sleep",
        "occurred_at": f"{(d - timedelta(days=1)).isoformat()}T23:00:00+00:00",
        "duration_sec": int(hours * 3600),
        "unit": "hr",
    }


def _rhr(d: date, value: float) -> dict:
    return {
        "sample_uuid": str(uuid.uuid4()),
        "sample_type": "rhr",
        "occurred_at": f"{d.isoformat()}T06:00:00+00:00",
        "value": value,
        "unit": "bpm",
    }


def _baseline_rhr(d: date, value: float, days: int = 30) -> list[dict]:
    return [_rhr(d - timedelta(days=i), value) for i in range(1, days + 1)]


# --- Pure sub-scores -------------------------------------------------------
def test_sub_scores_at_boundaries() -> None:
    assert sleep_score(8.0) == 100
    assert sleep_score(7.0) == 100 and sleep_score(9.0) == 100
    assert sleep_score(5.0) == 100 - (2 * 18)  # 64
    assert rhr_score(0) == 100 and rhr_score(-4) == 100
    assert rhr_score(10) == 30
    assert hrv_score(60, 60) == 100
    assert hrv_score(54, 60) == 80  # 10% below → -20
    assert sleep_score(2.0) == 10  # 100 - 5h*18
    assert sleep_score(0.0) == 0  # clamps, never negative


def test_one_night_change_does_not_swing_more_than_30_points() -> None:
    """§2.4 stop-condition: a realistic night-to-night change must not swing the
    composite > 30 points when all three inputs are present."""

    class S:
        def __init__(self, t, occ, val=None, dur=None):
            self.sample_type, self.occurred_at, self.value, self.duration_sec = t, occ, val, dur

    from datetime import datetime

    def night(target: date, sleep_h: float):
        samples = [
            S(
                "sleep",
                datetime(target.year, target.month, target.day - 1, 23, tzinfo=UTC),
                dur=int(sleep_h * 3600),
            ),
            S("rhr", datetime(target.year, target.month, target.day, 6, tzinfo=UTC), 56),
            S("hrv", datetime(target.year, target.month, target.day, 6, tzinfo=UTC), 60),
        ]
        # baseline rhr/hrv for the prior 30 days
        for i in range(1, 31):
            d = target - timedelta(days=i)
            samples.append(S("rhr", datetime(d.year, d.month, d.day, 6, tzinfo=UTC), 56))
            samples.append(S("hrv", datetime(d.year, d.month, d.day, 6, tzinfo=UTC), 60))
        return compute_readiness(samples, target)  # type: ignore[arg-type]

    good = night(TARGET, 8.0).score
    rough = night(TARGET, 6.0).score
    assert good is not None and rough is not None
    assert abs(good - rough) <= 30
    # And the swing is bounded by the sleep weight regardless of how bad sleep gets.
    terrible = night(TARGET, 3.0).score
    assert good - terrible <= round(W_SLEEP * 100) + 1


# --- Ingest idempotency ----------------------------------------------------
def test_healthkit_ingest_is_idempotent(client: Client) -> None:
    c, _ = client
    _create_profile(c)
    samples = [_sleep(TARGET, 8.0), _rhr(TARGET, 55)]

    first = c.post("/v1/wearable/healthkit", json={"samples": samples})
    assert first.status_code == 201, first.text
    assert first.json() == {"received": 2, "inserted": 2, "duplicates": 0}

    # Re-syncing HealthKit's rolling window re-sends the same UUIDs → no dupes.
    replay = c.post("/v1/wearable/healthkit", json={"samples": samples})
    assert replay.json() == {"received": 2, "inserted": 0, "duplicates": 2}


def test_healthkit_requires_auth(raw_client: TestClient) -> None:
    resp = raw_client.post("/v1/wearable/healthkit", json={"samples": [_sleep(TARGET, 8.0)]})
    assert resp.status_code == 401


# --- Readiness endpoint ----------------------------------------------------
def test_readiness_high_on_good_inputs(client: Client) -> None:
    c, _ = client
    _create_profile(c)
    samples = [_sleep(TARGET, 8.0), _rhr(TARGET, 55), *_baseline_rhr(TARGET, 58)]
    assert c.post("/v1/wearable/healthkit", json={"samples": samples}).status_code == 201

    r = c.get("/v1/athlete/readiness", params={"date": TARGET.isoformat()}).json()
    assert r["score"] == 100
    assert r["band"] == "high"
    assert {f["key"] for f in r["factors"]} == {"sleep", "rhr"}


def test_readiness_gates_on_poor_inputs(client: Client) -> None:
    c, _ = client
    _create_profile(c)
    # Short sleep + elevated resting HR (12 bpm over a 58 baseline).
    samples = [_sleep(TARGET, 5.5), _rhr(TARGET, 70), *_baseline_rhr(TARGET, 58)]
    assert c.post("/v1/wearable/healthkit", json={"samples": samples}).status_code == 201

    r = c.get("/v1/athlete/readiness", params={"date": TARGET.isoformat()}).json()
    assert 40 <= r["score"] <= 59
    assert r["band"] == "caution"


def test_readiness_unknown_without_data(client: Client) -> None:
    c, _ = client
    _create_profile(c)
    r = c.get("/v1/athlete/readiness", params={"date": TARGET.isoformat()}).json()
    assert r["score"] is None
    assert r["band"] == "unknown"
    assert r["factors"] == []
