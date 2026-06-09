"""API route contract tests (SQLite + fake Clerk + fake Anthropic)."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from tests.conftest import (
    JOSH_PROFILE,
    FakeAnthropic,
    draft_then_explain,
    end_turn,
    tool_use_block,
    usage,
)

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


# --- Health / auth ---------------------------------------------------------
def test_healthz_is_public(raw_client: TestClient) -> None:
    resp = raw_client.get("/v1/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_profile_requires_auth(raw_client: TestClient) -> None:
    assert raw_client.get("/v1/athlete/profile").status_code == 401


# --- Profile ---------------------------------------------------------------
def test_profile_upsert_and_get(client: Client) -> None:
    c, _ = client
    created = _create_profile(c)
    assert created["name"] == "Josh"
    assert created["estimated_1rm"]["deadlift"] == 336
    fetched = c.get("/v1/athlete/profile").json()
    assert fetched["id"] == created["id"]
    updated = c.post("/v1/athlete/profile", json={**JOSH_PROFILE, "days_per_week": 5}).json()
    assert updated["id"] == created["id"]  # upsert updates in place
    assert updated["days_per_week"] == 5


def test_get_profile_404_when_absent(client: Client) -> None:
    c, _ = client
    assert c.get("/v1/athlete/profile").status_code == 404


# --- Block creation runs the migrated planner ------------------------------
def test_create_block_produces_valid_plan(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    assert block["program_model"] == "hybrid_531"
    plan = block["plan_json"]
    assert plan is not None
    # The validated POC number: Back Squat TM wave 1 == 220.
    assert plan["training_maxes"][0]["tm_wave1"] == 220
    assert block["end_date"] is not None


def test_create_block_requires_profile(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    fake_anthropic.queue(*draft_then_explain())
    resp = c.post("/v1/blocks", json={"name": "x", "goal": "y"})
    assert resp.status_code == 404


def test_plan_and_messages_after_creation(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    bid = block["id"]

    plan = c.get(f"/v1/blocks/{bid}/plan").json()
    assert plan["plan"] is not None
    assert "program_model" in plan["summary"]

    page = c.get(f"/v1/blocks/{bid}/messages").json()
    assert page["total"] >= 2  # seeded user prompt + assistant reply
    assert any(m["cost_usd"] is not None for m in page["messages"])


def test_list_blocks(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    _create_block(c, fake_anthropic)
    blocks = c.get("/v1/blocks").json()
    assert len(blocks) == 1
    assert blocks[0]["name"] == "Crucible-25"


# --- Chat over SSE ---------------------------------------------------------
def test_chat_streams_sse(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    bid = block["id"]

    fake_anthropic.queue(end_turn("MAF cap is 146 bpm."))
    resp = c.post(f"/v1/blocks/{bid}/chat", json={"message": "What's my MAF cap?"})
    assert resp.status_code == 200
    body = resp.text
    assert "event: token" in body
    assert "event: done" in body
    assert "cost_usd" in body


# --- Plan edits: commit / reject -------------------------------------------
def _stage_edit(c: TestClient, fake: FakeAnthropic, bid: str) -> str:
    """Drive a chat turn that stages a swap; return the edit_id from the SSE stream."""
    fake.queue(
        SimpleNamespace(
            content=[
                tool_use_block(
                    "swap_lift",
                    "tu_swap",
                    {
                        "scope": "wave_1",
                        "day": "Fri",
                        "new_lift_key": "trap_bar_deadlift",
                        "new_display_name": "Trap Bar Deadlift",
                    },
                )
            ],
            stop_reason="tool_use",
            usage=usage(),
        ),
        end_turn("Staged the swap — approve?"),
    )
    resp = c.post(
        f"/v1/blocks/{bid}/chat",
        json={"message": "Swap Friday deadlift for trap bar, weeks 1-4"},
    )
    assert resp.status_code == 200
    body = resp.text
    assert "event: plan_edit" in body
    match = re.search(r"event: plan_edit\r?\ndata: (\{.*\})", body)
    assert match, body
    return json.loads(match.group(1))["edit_id"]


def test_commit_edit_applies_pending_plan(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    bid = block["id"]
    edit_id = _stage_edit(c, fake_anthropic, bid)

    resp = c.post(f"/v1/blocks/{bid}/edits/{edit_id}/commit")
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["plan_json"]["waves"][0]["training_maxes"].get("trap_bar_deadlift") == 285
    # Committing again is a conflict.
    assert c.post(f"/v1/blocks/{bid}/edits/{edit_id}/commit").status_code == 409


def test_reject_edit_leaves_plan_unchanged(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, _ = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    bid = block["id"]
    before = c.get(f"/v1/blocks/{bid}").json()["plan_json"]
    edit_id = _stage_edit(c, fake_anthropic, bid)

    assert c.post(f"/v1/blocks/{bid}/edits/{edit_id}/reject").status_code == 200
    after = c.get(f"/v1/blocks/{bid}").json()["plan_json"]
    assert after == before


# --- Ownership -------------------------------------------------------------
def test_block_ownership_isolation(client: Client, fake_anthropic: FakeAnthropic) -> None:
    c, set_user = client
    _create_profile(c)
    block = _create_block(c, fake_anthropic)
    bid = block["id"]
    set_user("user_b")  # a different user cannot see user_a's block
    assert c.get(f"/v1/blocks/{bid}").status_code == 404
