"""Wearable routes: HealthKit sample ingest (PRD §2.2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.auth.clerk import require_user
from obelisk_api.db.base import get_db
from obelisk_api.db.models import AthleteProfile, User
from obelisk_api.domain.schemas import WearableBatchIn, WearableBatchResult
from obelisk_api.ratelimit import limiter
from obelisk_api.services.wearable import ingest_samples

router = APIRouter(prefix="/wearable", tags=["wearable"])


def _profile_or_404(db: Session, user: User) -> AthleteProfile:
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No athlete profile yet")
    return profile


@router.post("/healthkit", response_model=WearableBatchResult, status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
def ingest_healthkit(
    request: Request,
    payload: WearableBatchIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> WearableBatchResult:
    """Ingest a batch of HealthKit samples (idempotent on the HKObject UUID)."""
    profile = _profile_or_404(db, user)
    inserted, duplicates = ingest_samples(db, profile.id, payload.samples)
    return WearableBatchResult(
        received=len(payload.samples), inserted=inserted, duplicates=duplicates
    )
