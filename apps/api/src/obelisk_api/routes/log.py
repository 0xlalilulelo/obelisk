"""Log routes: batched set ingestion (In-Session) + the unified Log feed.

``POST /v1/log`` is the sync target for the on-device set queue — idempotent on a
client-generated UUID so a reconnect after lost signal never double-logs (PRD §2.1).
``GET /v1/log`` backs the Log tab.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from obelisk_api.auth.clerk import require_user
from obelisk_api.db.base import get_db
from obelisk_api.db.models import AthleteProfile, LogEntry, User
from obelisk_api.domain.schemas import LogBatchIn, LogBatchResult, LogPage
from obelisk_api.ratelimit import limiter
from obelisk_api.services.logbook import insert_set_logs

router = APIRouter(prefix="/log", tags=["log"])


def _profile_or_404(db: Session, user: User) -> AthleteProfile:
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No athlete profile yet")
    return profile


@router.post("", response_model=LogBatchResult, status_code=status.HTTP_201_CREATED)
@limiter.limit("120/minute")
def post_log(
    request: Request,
    payload: LogBatchIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> LogBatchResult:
    """Idempotently persist a batch of logged sets flushed from the device queue."""
    profile = _profile_or_404(db, user)
    inserted, duplicates = insert_set_logs(db, profile.id, payload.sets)
    return LogBatchResult(received=len(payload.sets), inserted=inserted, duplicates=duplicates)


@router.get("", response_model=LogPage)
@limiter.limit("120/minute")
def list_log(
    request: Request,
    type: str | None = Query(default=None, description="Filter by entry type, e.g. 'set'."),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> LogPage:
    """The athlete's log feed, newest first."""
    profile = _profile_or_404(db, user)
    base = select(LogEntry).where(LogEntry.athlete_id == profile.id)
    if type:
        base = base.where(LogEntry.type == type)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(base.order_by(LogEntry.occurred_at.desc()).limit(limit).offset(offset)).all()
    return LogPage(entries=list(rows), total=total, limit=limit, offset=offset)
