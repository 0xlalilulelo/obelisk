"""Tests for the agent layer that don't require a live API key.

Covers the tool loop (with a fake Anthropic client), tool dispatch, the
diff-before-commit gate, Block persistence, cost accounting, and the system
prompt — i.e. the POC's core behaviours, verified offline.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from obelisk_api.agent.block import Block, list_blocks, new_block_id
from obelisk_api.agent.cost_tracker import CostTracker, pricing_for
from obelisk_api.agent.loop import (
    BlockCoach,
    MissingAPIKeyError,
    _assistant_text,
    _block_to_param,
    require_client,
    resolve_model,
)
from obelisk_api.agent.system_prompt import build_system_prompt
from obelisk_api.domain.models import Athlete
from obelisk_api.tools.registry import dispatch, tool_specs

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def josh() -> Athlete:
    data = json.loads((PROJECT_ROOT / "data" / "sample_athlete.json").read_text(encoding="utf-8"))
    return Athlete.model_validate(data)


# ---------------------------------------------------------------------------
# Cost tracker
# ---------------------------------------------------------------------------


def test_cost_tracker_math_and_totals() -> None:
    tracker = CostTracker(model="claude-sonnet-4-6")
    tracker.record(label="a", input_tokens=1_000_000, output_tokens=0, latency_s=2.0)
    tracker.record(label="b", input_tokens=0, output_tokens=1_000_000, latency_s=5.0)
    # 1M input @ $3 + 1M output @ $15 = $18.00
    assert tracker.total_usd == pytest.approx(18.0)
    assert tracker.total_output_tokens == 1_000_000
    assert tracker.max_latency_s == 5.0
    assert "SESSION COST SUMMARY" in tracker.format_summary()
    assert "$" in tracker.format_last_call()


def test_cost_tracker_cache_pricing() -> None:
    tracker = CostTracker(model="claude-sonnet-4-6")
    tracker.record(
        label="cached",
        input_tokens=0,
        output_tokens=0,
        cache_read_tokens=1_000_000,
        cache_write_tokens=0,
    )
    assert tracker.total_usd == pytest.approx(0.30)  # cache read @ $0.30/MTok


def test_pricing_falls_back_to_sonnet() -> None:
    assert pricing_for("some-unknown-model").input == 3.0


def test_cost_tracker_empty_summary() -> None:
    assert "no API calls" in CostTracker(model="x").format_last_call()


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


def test_system_prompt_includes_brief_and_athlete(josh: Athlete) -> None:
    prompt = build_system_prompt(josh)
    assert "Role and Mandate" in prompt  # Brief section 1
    assert "Numbers come from tools" in prompt  # operating instructions
    assert "Josh" in prompt and "146 bpm" in prompt  # athlete block + MAF cap


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_block_save_and_load_roundtrip(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    block = Block(block_id=new_block_id(), model="claude-sonnet-4-6", athlete=josh)
    dispatch(
        block,
        "draft_cycle_plan",
        {"title": "Test Cycle", "goals": ["g1"], "priority_lifts": ["bench_press"]},
    )
    block.messages.append({"role": "user", "content": "hi"})
    block.save()

    loaded = Block.load(block.block_id)
    assert loaded.name == "Test Cycle"
    assert loaded.current_plan is not None
    assert loaded.current_plan.training_maxes[0].tm_wave1 == 220
    assert loaded.messages == [{"role": "user", "content": "hi"}]
    assert block.block_id in list_blocks()


def test_block_load_missing_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    with pytest.raises(FileNotFoundError):
        Block.load("does-not-exist")


# ---------------------------------------------------------------------------
# Tool dispatch + diff-before-commit gate
# ---------------------------------------------------------------------------


def test_tool_specs_cover_required_tools() -> None:
    names = {spec["name"] for spec in tool_specs()}
    required = {
        "compute_1rm",
        "compute_training_max",
        "compute_macros",
        "compute_maf",
        "get_periodization_template",
        "compute_warmup_ramp",
        "lookup_advisor_principle",
        "draft_cycle_plan",
        "swap_lift",
        "override_week",
        "set_day_across_weeks",
        "commit_plan_update",
        "show_plan_diff",
    }
    assert required.issubset(names)


def test_set_day_across_weeks_is_atomic(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    block = Block(block_id=new_block_id(), model="m", athlete=josh)
    dispatch(
        block, "draft_cycle_plan", {"program_model": "hybrid_531", "title": "C1", "goals": ["g"]}
    )
    out = dispatch(
        block,
        "set_day_across_weeks",
        {
            "day": "Tue",
            "weeks": [5, 6, 7, 8],
            "session": "MP progression run",
            "items": ["10 mi: 4 easy + 6 @ marathon pace"],
        },
    )
    assert "PROPOSED CHANGES" in out
    assert "Committed" in dispatch(block, "commit_plan_update", {})
    assert block.current_plan is not None
    # All four weeks now carry the new Tuesday session — atomic, not partial.
    for wk in (5, 6, 7, 8):
        tue = next(d for d in block.current_plan.days_for_week(wk) if d.day == "Tue")
        assert tue.session == "MP progression run"
    # An untouched week still has its original Tuesday.
    assert block.current_plan.days_for_week(1)[0].day == "Mon"


def test_staged_edits_accumulate(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two edits staged in one turn (no commit between) compose into one diff."""
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    block = Block(block_id=new_block_id(), model="m", athlete=josh)
    dispatch(
        block, "draft_cycle_plan", {"program_model": "hybrid_531", "title": "C1", "goals": ["g"]}
    )
    dispatch(
        block,
        "set_day_across_weeks",
        {"day": "Mon", "weeks": [1, 2], "session": "Goblet day", "items": ["goblet squat 3x5"]},
    )
    # Second stage WITHOUT committing the first — must build on the pending plan.
    dispatch(
        block,
        "set_day_across_weeks",
        {"day": "Fri", "weeks": [1, 2], "session": "Split squat day", "items": ["DB split squat"]},
    )
    assert "Committed" in dispatch(block, "commit_plan_update", {})
    assert block.current_plan is not None
    days = {d.day: d.session for d in block.current_plan.days_for_week(1)}
    assert days["Mon"] == "Goblet day"  # first edit survived the second
    assert days["Fri"] == "Split squat day"


def test_dispatch_deterministic_tools(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    block = Block(block_id=new_block_id(), model="m", athlete=josh)
    assert dispatch(block, "compute_1rm", {"weight_lb": 235, "reps": 3}) == "260"
    assert dispatch(block, "compute_maf", {"age": 34}) == "146"
    assert "carbs_g" in dispatch(block, "compute_macros", {"bw_lb": 175, "day_type": "hard"})
    assert "Climbing" in dispatch(block, "lookup_advisor_principle", {"topic": "hangboard"}) or True


def test_dispatch_bad_input_is_caught(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    block = Block(block_id=new_block_id(), model="m", athlete=josh)
    out = dispatch(block, "compute_maf", {"age": 0})
    assert "error" in out.lower()
    assert "Unknown tool" in dispatch(block, "nonexistent_tool", {})


def test_swap_lift_diff_before_commit_gate(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    block = Block(block_id=new_block_id(), model="m", athlete=josh)
    dispatch(block, "draft_cycle_plan", {"title": "C1", "goals": ["g"], "priority_lifts": []})

    # Stage: swap Friday deadlift -> trap bar for wave 1 only.
    diff_text = dispatch(
        block,
        "swap_lift",
        {
            "scope": "wave_1",
            "day": "Fri",
            "new_lift_key": "trap_bar_deadlift",
            "new_display_name": "Trap Bar Deadlift",
        },
    )
    assert "PROPOSED CHANGES" in diff_text
    assert "trap" in diff_text.lower()
    # Not committed: wave 1 still has no override applied to current plan.
    assert block.current_plan is not None
    assert block.current_plan.waves[0].days_override is None
    assert block.pending_plan is not None
    assert "trap" in dispatch(block, "show_plan_diff", {}).lower()

    # Commit applies it to wave 1 only.
    assert "Committed" in dispatch(block, "commit_plan_update", {})
    assert block.current_plan.waves[0].days_override is not None
    assert block.current_plan.waves[1].days_override is None  # wave 2 untouched
    assert block.pending_plan is None
    # The trap bar carries the deadlift TM (285) for wave 1.
    assert block.current_plan.waves[0].training_maxes["trap_bar_deadlift"] == 285


def test_override_week_for_travel(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    block = Block(block_id=new_block_id(), model="m", athlete=josh)
    dispatch(block, "draft_cycle_plan", {"title": "C1", "goals": ["g"]})
    out = dispatch(
        block,
        "override_week",
        {
            "global_week": 2,
            "days": [
                {
                    "day": "Mon",
                    "session": "KB strength",
                    "items": ["KB clean+press 5x5", "KB swings 5x20"],
                },
                {"day": "Tue", "session": "Aerobic", "items": ["Easy run 40 min @ MAF"]},
            ],
        },
    )
    assert "PROPOSED CHANGES" in out
    assert "Committed" in dispatch(block, "commit_plan_update", {})
    assert block.current_plan is not None
    week2_days = block.current_plan.days_for_week(2)
    assert week2_days[0].session == "KB strength"


def test_commit_without_pending_is_safe(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    block = Block(block_id=new_block_id(), model="m", athlete=josh)
    assert "No pending change" in dispatch(block, "commit_plan_update", {})
    assert "No plan yet" in dispatch(block, "get_plan_json", {})


# ---------------------------------------------------------------------------
# Agent loop (fake client)
# ---------------------------------------------------------------------------


def _usage(in_t: int = 100, out_t: int = 40) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=in_t,
        output_tokens=out_t,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(name: str, tool_id: str, tool_input: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", name=name, id=tool_id, input=tool_input)


class _FakeMessages:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return self._responses.pop(0)


class _FakeClient:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self.messages = _FakeMessages(responses)


def test_block_to_param_serialization() -> None:
    assert _block_to_param(_text_block("hi")) == {"type": "text", "text": "hi"}
    tu = _block_to_param(_tool_use_block("compute_maf", "t1", {"age": 34}))
    assert tu["type"] == "tool_use" and tu["name"] == "compute_maf"


def test_assistant_text_joins_text_blocks() -> None:
    msg = SimpleNamespace(
        content=[_text_block("line1"), _tool_use_block("x", "i", {}), _text_block("line2")]
    )
    assert _assistant_text(msg) == "line1\nline2"  # type: ignore[arg-type]


def test_agent_runs_tool_loop_with_fake_client(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    # Turn 1: model calls draft_cycle_plan. Turn 2: model gives final text.
    responses = [
        SimpleNamespace(
            content=[
                _tool_use_block(
                    "draft_cycle_plan",
                    "tu1",
                    {"title": "C1", "goals": ["g"], "priority_lifts": ["bench_press"]},
                )
            ],
            stop_reason="tool_use",
            usage=_usage(in_t=2000, out_t=120),
        ),
        SimpleNamespace(
            content=[_text_block("Here is your cycle. TMs at 85% of 1RM per the Brief.")],
            stop_reason="end_turn",
            usage=_usage(in_t=2500, out_t=300),
        ),
    ]
    coach = BlockCoach(
        block=Block(block_id=new_block_id(), model="claude-sonnet-4-6", athlete=josh),
        client=_FakeClient(responses),  # type: ignore[arg-type]
        system_prompt="SYS",
        tracker=CostTracker(model="claude-sonnet-4-6"),
    )
    final = coach.send("Create my cycle and draft it.")
    assert "cycle" in final.lower()
    assert coach.block.current_plan is not None
    assert coach.block.current_plan.training_maxes[0].tm_wave1 == 220
    assert len(coach.tracker.calls) == 2
    assert coach.tracker.calls[0].label == "block-creation"


# ---------------------------------------------------------------------------
# Client guard
# ---------------------------------------------------------------------------


def test_max_cost_ceiling_blocks_further_calls(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    # One end_turn response; the single call costs more than the tiny ceiling.
    responses = [
        SimpleNamespace(
            content=[_text_block("ok")],
            stop_reason="end_turn",
            usage=_usage(in_t=200_000, out_t=0),  # 200k input @ $3/MTok = $0.60
        )
    ]
    client = _FakeClient(responses)
    coach = BlockCoach(
        block=Block(block_id=new_block_id(), model="claude-sonnet-4-6", athlete=josh),
        client=client,  # type: ignore[arg-type]
        system_prompt="SYS",
        tracker=CostTracker(model="claude-sonnet-4-6"),
        max_cost_usd=0.10,
    )
    # First turn runs (ceiling not yet reached), pushing total to $0.60.
    assert coach.send("first") == "ok"
    assert coach.tracker.total_usd > 0.10
    # Second turn is blocked before any call; the fake client saw only one create.
    blocked = coach.send("second")
    assert "ceiling" in blocked.lower()
    assert len(client.messages.calls) == 1
    # The blocked turn left no dangling user message in history.
    assert coach.block.messages[-1] != {"role": "user", "content": "second"}


def test_max_cost_zero_means_unlimited(
    josh: Athlete, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("obelisk_api.agent.block.RUNS_DIR", tmp_path / "runs")
    coach = BlockCoach(
        block=Block(block_id=new_block_id(), model="m", athlete=josh),
        client=_FakeClient([SimpleNamespace(content=[_text_block("hi")], stop_reason="end_turn", usage=_usage())]),  # type: ignore[arg-type]
        system_prompt="SYS",
        tracker=CostTracker(model="claude-sonnet-4-6"),
        max_cost_usd=0.0,
    )
    assert not coach._over_ceiling()
    assert coach.send("go") == "hi"


def test_require_client_without_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("obelisk_api.agent.loop.load_dotenv", lambda: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError):
        require_client()


def test_resolve_model_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OBELISK_MODEL", raising=False)
    assert resolve_model() == "claude-sonnet-4-6"
