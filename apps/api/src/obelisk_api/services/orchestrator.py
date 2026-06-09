"""Bridge between Postgres persistence and the validated in-memory agent (ADR-005).

Hydrate an agent ``Block`` from DB rows → run the validated tool-use loop → persist
the new messages (with per-turn cost), the updated ``plan_json``, and any staged
``PlanEdit``. The agent loop itself is untouched; this module is the only new seam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from anthropic import Anthropic
from sqlalchemy.orm import Session

from obelisk_api.agent.block import Block as AgentBlock
from obelisk_api.agent.cost_tracker import CostTracker
from obelisk_api.agent.loop import BlockCoach
from obelisk_api.agent.system_prompt import build_system_prompt
from obelisk_api.config import get_settings
from obelisk_api.db import models as orm
from obelisk_api.domain.models import Athlete, CyclePlan, EstimatedOneRepMax
from obelisk_api.services.diff import format_diff

_NEW_BLOCK_PROMPT = (
    "Create my training cycle. Goal: {goal}\n\n"
    "Choose the program model that fits me, draft the plan with the tool, then explain "
    "— concisely — the structure. For each major decision cite both the Advisor Brief "
    "principle and the specific baseline number of mine that drives it."
)

_1RM_FIELDS = set(EstimatedOneRepMax.model_fields)


@dataclass
class TurnResult:
    final_text: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    latency_ms: int
    tool_names: list[str] = field(default_factory=list)
    assistant_message_id: Any = None
    staged_edit_id: Any = None
    diff_text: str | None = None


def profile_to_athlete(profile: orm.AthleteProfile) -> Athlete:
    """Map a persisted profile into the agent's domain ``Athlete``."""
    rm = {k: v for k, v in (profile.estimated_1rm or {}).items() if k in _1RM_FIELDS}
    data: dict[str, Any] = {
        "name": profile.name,
        "age": profile.age,
        "bodyweight_lb": profile.bodyweight_lb if profile.bodyweight_lb is not None else 0.0,
        "height_in": profile.height_in,
        "resting_hr_bpm": profile.resting_hr_bpm,
        "sex": profile.sex,
        "estimated_1rm": EstimatedOneRepMax(**rm) if rm else None,
        "rep_max_known": profile.rep_max_known,
        "primary_goals": list(profile.primary_goals or []),
        "equipment": profile.equipment,
        "days_per_week": profile.days_per_week,
        "injuries": [
            (inj.get("description") if isinstance(inj, dict) else str(inj))
            for inj in (profile.injuries or [])
        ],
    }
    if profile.maf_data:
        data.update(profile.maf_data)
    return Athlete.model_validate(data)


def _ensure_conversation(db: Session, db_block: orm.Block) -> orm.Conversation:
    if db_block.conversation is None:
        conv = orm.Conversation(block_id=db_block.id)
        db.add(conv)
        db.flush()
        db_block.conversation = conv
    return db_block.conversation


def _prior_messages(conv: orm.Conversation) -> list[dict[str, Any]]:
    ordered = sorted(conv.messages, key=lambda m: m.created_at)
    return [{"role": m.role, "content": m.content} for m in ordered]


def _persist_messages(
    db: Session,
    conv: orm.Conversation,
    new_messages: list[dict[str, Any]],
    *,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    latency_ms: int,
) -> Any:
    """Persist a turn's messages in order; attach cost to the final assistant row."""
    base = datetime.now(UTC)
    last_assistant_idx = max(
        (i for i, m in enumerate(new_messages) if m.get("role") == "assistant"),
        default=len(new_messages) - 1,
    )
    assistant_id = None
    for i, msg in enumerate(new_messages):
        is_cost_row = i == last_assistant_idx
        row = orm.Message(
            conversation_id=conv.id,
            role=str(msg.get("role", "assistant")),
            content=msg.get("content"),
            tokens_in=tokens_in if is_cost_row else None,
            tokens_out=tokens_out if is_cost_row else None,
            cost_usd=cost_usd if is_cost_row else None,
            latency_ms=latency_ms if is_cost_row else None,
            created_at=base + timedelta(microseconds=i),
        )
        db.add(row)
        db.flush()
        if is_cost_row:
            assistant_id = row.id
    return assistant_id


def _tool_names(new_messages: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for msg in new_messages:
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    names.append(str(block.get("name")))
    return names


def run_turn(
    db: Session,
    db_block: orm.Block,
    user_text: str,
    client: Anthropic,
) -> TurnResult:
    """Run one agent turn against a Block, persisting messages + plan + staged edits."""
    settings = get_settings()
    athlete = profile_to_athlete(db_block.athlete)
    conv = _ensure_conversation(db, db_block)
    prior = _prior_messages(conv)

    current_plan = CyclePlan.model_validate(db_block.plan_json) if db_block.plan_json else None
    agent_block = AgentBlock(
        block_id=str(db_block.id),
        model=settings.obelisk_model,
        athlete=athlete,
        name=db_block.name,
        current_plan=current_plan,
        messages=list(prior),
    )
    # In the API we persist to Postgres, not JSON files — neutralize file writes.
    agent_block.save = lambda: None  # type: ignore[method-assign]

    coach = BlockCoach(
        block=agent_block,
        client=client,
        system_prompt=build_system_prompt(athlete),
        tracker=CostTracker(model=settings.obelisk_model),
        max_cost_usd=settings.max_cost_usd,
    )

    prior_len = len(agent_block.messages)
    final_text = coach.send(user_text)
    new_messages = agent_block.messages[prior_len:]

    tokens_in = coach.tracker.total_input_tokens
    tokens_out = coach.tracker.total_output_tokens
    cost_usd = coach.tracker.total_usd
    latency_ms = int(coach.tracker.max_latency_s * 1000)

    assistant_id = _persist_messages(
        db,
        conv,
        new_messages,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
    )

    if agent_block.current_plan is not None:
        db_block.plan_json = agent_block.current_plan.model_dump()
        db_block.program_model = agent_block.current_plan.program_model

    # A staged-but-uncommitted edit becomes an event-sourced PlanEdit row.
    staged_edit_id = None
    diff_text = None
    if agent_block.pending_plan is not None and agent_block.last_diff is not None:
        diff_text = format_diff(agent_block.last_diff)
        edit = orm.PlanEdit(
            block_id=db_block.id,
            edit_type=agent_block.last_diff.summary[:120],
            payload={
                "diff": diff_text,
                "pending_plan": agent_block.pending_plan.model_dump(),
            },
            staged=True,
        )
        db.add(edit)
        db.flush()
        staged_edit_id = edit.id

    return TurnResult(
        final_text=final_text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        tool_names=_tool_names(new_messages),
        assistant_message_id=assistant_id,
        staged_edit_id=staged_edit_id,
        diff_text=diff_text,
    )


def create_block(
    db: Session,
    profile: orm.AthleteProfile,
    name: str,
    goal: str,
    client: Anthropic,
    program_model: str | None = None,
) -> orm.Block:
    """Create a Block and run the planner turn so plan_json is populated."""
    db_block = orm.Block(
        athlete_id=profile.id,
        name=name,
        goal=goal,
        program_model=program_model or "hybrid_531",
        phase="active",
        start_date=date.today(),
    )
    db.add(db_block)
    db.flush()
    db_block.athlete = profile

    run_turn(db, db_block, _NEW_BLOCK_PROMPT.format(goal=goal), client)

    # Derive end_date from the drafted plan's length (waves × 4 weeks).
    if db_block.plan_json:
        plan = CyclePlan.model_validate(db_block.plan_json)
        total_weeks = max(len(plan.waves) * 4, 1)
        db_block.end_date = date.today() + timedelta(weeks=total_weeks)
    return db_block
