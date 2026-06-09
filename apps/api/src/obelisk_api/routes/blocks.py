"""Block routes: create (planner), read, plan, chat (SSE), messages, edits, artifact."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

from anthropic import Anthropic
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from starlette.concurrency import run_in_threadpool

from obelisk_api.auth.clerk import require_user
from obelisk_api.db.base import get_db
from obelisk_api.db.models import (
    AthleteProfile,
    Block,
    Message,
    PlanEdit,
    User,
)
from obelisk_api.deps import get_anthropic_client
from obelisk_api.domain.models import CyclePlan
from obelisk_api.domain.schemas import (
    ArtifactUrlOut,
    BlockCreateIn,
    BlockOut,
    BlockSummaryOut,
    ChatIn,
    MessageOut,
    MessagePage,
    PlanEditOut,
    PlanOut,
)
from obelisk_api.services import orchestrator, storage
from obelisk_api.tools.registry import _plan_summary

router = APIRouter(prefix="/blocks", tags=["blocks"])


def _profile_or_404(db: Session, user: User) -> AthleteProfile:
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Create an athlete profile before creating a Block.",
        )
    return profile


def _owned_block(db: Session, user: User, block_id: uuid.UUID) -> Block:
    block = db.scalar(
        select(Block)
        .join(AthleteProfile, Block.athlete_id == AthleteProfile.id)
        .where(Block.id == block_id, AthleteProfile.user_id == user.id)
    )
    if block is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found")
    return block


@router.post("", response_model=BlockOut, status_code=status.HTTP_201_CREATED)
def create_block(
    payload: BlockCreateIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    client: Anthropic = Depends(get_anthropic_client),
) -> Block:
    profile = _profile_or_404(db, user)
    if profile.bodyweight_lb is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Profile needs a bodyweight before the coach can plan.",
        )
    return orchestrator.create_block(
        db, profile, payload.name, payload.goal, client, payload.program_model
    )


@router.get("", response_model=list[BlockSummaryOut])
def list_blocks(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[Block]:
    rows = db.scalars(
        select(Block)
        .join(AthleteProfile, Block.athlete_id == AthleteProfile.id)
        .where(AthleteProfile.user_id == user.id)
        .order_by(Block.created_at.desc())
    ).all()
    return list(rows)


@router.get("/{block_id}", response_model=BlockOut)
def get_block(
    block_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Block:
    return _owned_block(db, user, block_id)


@router.get("/{block_id}/plan", response_model=PlanOut)
def get_plan(
    block_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PlanOut:
    block = _owned_block(db, user, block_id)
    if not block.plan_json:
        return PlanOut(plan=None, summary="No plan yet.")
    plan = CyclePlan.model_validate(block.plan_json)
    return PlanOut(plan=block.plan_json, summary=_plan_summary(plan))


@router.get("/{block_id}/messages", response_model=MessagePage)
def get_messages(
    block_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> MessagePage:
    block = _owned_block(db, user, block_id)
    if block.conversation is None:
        return MessagePage(messages=[], total=0, limit=limit, offset=offset)
    conv_id = block.conversation.id
    total = db.scalar(
        select(func.count()).select_from(Message).where(Message.conversation_id == conv_id)
    )
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return MessagePage(
        messages=[MessageOut.model_validate(r) for r in rows],
        total=total or 0,
        limit=limit,
        offset=offset,
    )


def _chunk_text(text: str, words_per_chunk: int = 6) -> list[str]:
    """Split assistant text into chunks for a token-stream feel (ADR-006)."""
    words = text.split(" ")
    return [
        " ".join(words[i : i + words_per_chunk]) + (" " if i + words_per_chunk < len(words) else "")
        for i in range(0, len(words), words_per_chunk)
    ]


@router.post("/{block_id}/chat")
async def chat(
    block_id: uuid.UUID,
    payload: ChatIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
    client: Anthropic = Depends(get_anthropic_client),
) -> EventSourceResponse:
    """Append a user message, run the agent loop, stream the response over SSE."""
    block = _owned_block(db, user, block_id)

    async def event_gen() -> AsyncIterator[dict[str, Any]]:
        yield {"event": "open", "data": json.dumps({"block_id": str(block_id)})}
        try:
            result = await run_in_threadpool(
                orchestrator.run_turn, db, block, payload.message, client
            )
        except Exception as exc:  # surface a user-safe error, log detail server-side
            yield {"event": "error", "data": json.dumps({"message": str(exc)[:300]})}
            return
        for name in result.tool_names:
            yield {"event": "tool_use", "data": json.dumps({"name": name})}
        for chunk in _chunk_text(result.final_text):
            yield {"event": "token", "data": json.dumps({"text": chunk})}
        if result.staged_edit_id is not None:
            yield {
                "event": "plan_edit",
                "data": json.dumps(
                    {"edit_id": str(result.staged_edit_id), "diff": result.diff_text}
                ),
            }
        yield {
            "event": "done",
            "data": json.dumps(
                {
                    "message_id": (
                        str(result.assistant_message_id) if result.assistant_message_id else None
                    ),
                    "cost_usd": result.cost_usd,
                    "tokens_in": result.tokens_in,
                    "tokens_out": result.tokens_out,
                    "latency_ms": result.latency_ms,
                }
            ),
        }

    return EventSourceResponse(event_gen())


def _staged_edit_or_404(db: Session, block: Block, edit_id: uuid.UUID) -> PlanEdit:
    edit = db.scalar(select(PlanEdit).where(PlanEdit.id == edit_id, PlanEdit.block_id == block.id))
    if edit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edit not found")
    return edit


@router.post("/{block_id}/edits/{edit_id}/commit", response_model=BlockOut)
def commit_edit(
    block_id: uuid.UUID,
    edit_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> Block:
    block = _owned_block(db, user, block_id)
    edit = _staged_edit_or_404(db, block, edit_id)
    if not edit.staged:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Edit already resolved")
    pending = (edit.payload or {}).get("pending_plan")
    if pending is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Edit has no pending plan"
        )
    block.plan_json = pending
    block.program_model = CyclePlan.model_validate(pending).program_model
    edit.staged = False
    edit.committed_at = func.now()
    db.flush()
    return block


@router.post("/{block_id}/edits/{edit_id}/reject", response_model=PlanEditOut)
def reject_edit(
    block_id: uuid.UUID,
    edit_id: uuid.UUID,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PlanEdit:
    block = _owned_block(db, user, block_id)
    edit = _staged_edit_or_404(db, block, edit_id)
    if not edit.staged:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Edit already resolved")
    edit.staged = False  # resolved without committing; plan_json unchanged
    db.flush()
    return edit


@router.get("/{block_id}/artifact/{kind}", response_model=ArtifactUrlOut)
def get_artifact(
    block_id: uuid.UUID,
    kind: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> ArtifactUrlOut:
    block = _owned_block(db, user, block_id)
    if not block.plan_json:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No artifact yet")
    return ArtifactUrlOut(
        kind=kind, url=storage.presigned_artifact_url(str(block.id), kind), version=1
    )
