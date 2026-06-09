"""Athlete profile routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.auth.clerk import require_user
from obelisk_api.db.base import get_db
from obelisk_api.db.models import AthleteProfile, User
from obelisk_api.domain.schemas import AthleteProfileIn, AthleteProfileOut

router = APIRouter(prefix="/athlete", tags=["athlete"])


def _get_profile(db: Session, user: User) -> AthleteProfile | None:
    return db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))


@router.post("/profile", response_model=AthleteProfileOut)
def upsert_profile(
    payload: AthleteProfileIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> AthleteProfile:
    """Create or update the caller's athlete profile (5-question onboarding output)."""
    profile = _get_profile(db, user)
    fields = payload.model_dump()
    if profile is None:
        profile = AthleteProfile(user_id=user.id, **fields)
        db.add(profile)
    else:
        for key, value in fields.items():
            setattr(profile, key, value)
    db.flush()
    return profile


@router.get("/profile", response_model=AthleteProfileOut)
def get_profile(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> AthleteProfile:
    profile = _get_profile(db, user)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No athlete profile yet")
    return profile
