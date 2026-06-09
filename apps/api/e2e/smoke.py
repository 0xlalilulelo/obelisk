"""End-to-end happy-path smoke: profile → block → plan → chat, against real Postgres.

Runs the real FastAPI app and real DB (DATABASE_URL). Only the two external services
are faked — Clerk (injected claims) and Anthropic (a scripted draft) — so the smoke
needs no secrets and spends no tokens. Exits non-zero on any failure.
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

from obelisk_api.auth.clerk import get_token_claims
from obelisk_api.deps import get_anthropic_client
from obelisk_api.main import create_app


def _usage() -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=2000,
        output_tokens=120,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


class _FakeMessages:
    def __init__(self) -> None:
        self._scripted: list[SimpleNamespace] = [
            SimpleNamespace(
                content=[
                    SimpleNamespace(
                        type="tool_use",
                        name="draft_cycle_plan",
                        id="tu1",
                        input={
                            "program_model": "hybrid_531",
                            "title": "Smoke-Block",
                            "goals": ["aerobic base + strength"],
                            "priority_lifts": ["bench_press"],
                        },
                    )
                ],
                stop_reason="tool_use",
                usage=_usage(),
            ),
            SimpleNamespace(
                content=[SimpleNamespace(type="text", text="Drafted your cycle.")],
                stop_reason="end_turn",
                usage=_usage(),
            ),
        ]

    def create(self, **_: Any) -> SimpleNamespace:
        if self._scripted:
            return self._scripted.pop(0)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Your MAF cap is 146 bpm.")],
            stop_reason="end_turn",
            usage=_usage(),
        )


class _FakeAnthropic:
    def __init__(self) -> None:
        self.messages = _FakeMessages()


def main() -> int:
    app = create_app()
    app.dependency_overrides[get_token_claims] = lambda: {"sub": "smoke_user", "email": "s@e.com"}
    app.dependency_overrides[get_anthropic_client] = lambda: _FakeAnthropic()

    with TestClient(app) as c:
        assert c.get("/v1/healthz").json() == {"status": "ok"}, "healthz failed"

        profile = {
            "name": "SmokeAthlete",
            "age": 34,
            "bodyweight_lb": 175,
            "estimated_1rm": {
                "back_squat": 259,
                "deadlift": 336,
                "bench_press": 182,
                "strict_press": 123,
                "front_squat": 248,
                "power_clean": 182,
            },
            "primary_goals": ["strength"],
            "equipment": "full_gym",
            "days_per_week": 6,
        }
        r = c.post("/v1/athlete/profile", json=profile)
        assert r.status_code == 200, f"profile create: {r.status_code} {r.text}"

        r = c.post("/v1/blocks", json={"name": "Smoke-Block", "goal": "strength"})
        assert r.status_code == 201, f"block create: {r.status_code} {r.text}"
        block = r.json()
        assert block["plan_json"], "block has no plan_json"
        assert block["plan_json"]["training_maxes"][0]["tm_wave1"] == 220, "wrong TM"
        bid = block["id"]

        r = c.post(f"/v1/blocks/{bid}/chat", json={"message": "What is my MAF cap?"})
        assert r.status_code == 200, f"chat: {r.status_code}"
        assert "event: done" in r.text, "chat stream had no done event"
        assert "event: token" in r.text, "chat stream had no tokens"

        page = c.get(f"/v1/blocks/{bid}/messages").json()
        assert page["total"] >= 4, f"expected persisted messages, got {page['total']}"

    print("E2E smoke PASSED: profile → block → plan(TM=220) → chat(SSE) → messages persisted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
