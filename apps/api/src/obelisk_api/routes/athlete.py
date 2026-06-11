"""Athlete profile routes."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.auth.clerk import require_user
from obelisk_api.db.base import get_db
from obelisk_api.db.models import AthleteProfile, User, WearableSample
from obelisk_api.domain.schemas import (
    AnalyticsLiftsOut,
    AthleteProfileIn,
    AthleteProfileOut,
    LiftPointOut,
    PROut,
    ReadinessFactorOut,
    ReadinessOut,
)
from obelisk_api.ratelimit import limiter
from obelisk_api.services.logbook import best_e1rm, e1rm_series
from obelisk_api.services.readiness import compute_readiness

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


@router.get("/pr/{lift}", response_model=PROut)
@limiter.limit("120/minute")
def get_pr(
    request: Request,
    lift: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> PROut:
    """Current estimated 1RM for a lift, used by in-session PR detection. Prefers
    the best Epley e1RM across logged sets; falls back to the profile's baseline."""
    profile = _get_profile(db, user)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No athlete profile yet")
    best = best_e1rm(db, profile.id, lift)
    if best is not None:
        return PROut(
            lift=lift,
            e1rm=best["e1rm"],
            source="logged",
            weight_lb=best["weight_lb"],
            reps=best["reps"],
            occurred_at=best["occurred_at"],
        )
    baseline = (profile.estimated_1rm or {}).get(lift)
    if baseline:
        return PROut(lift=lift, e1rm=int(baseline), source="profile")
    return PROut(lift=lift, e1rm=None, source="none")


@router.get("/analytics/lifts", response_model=AnalyticsLiftsOut)
@limiter.limit("60/minute")
def get_lift_analytics(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> AnalyticsLiftsOut:
    """Per-lift e1RM curves from logged sets, for the desktop Analytics charts."""
    profile = _get_profile(db, user)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No athlete profile yet")
    series = e1rm_series(db, profile.id)
    return AnalyticsLiftsOut(
        series={
            lift: [LiftPointOut(date=date.fromisoformat(p["date"]), e1rm=p["e1rm"]) for p in points]
            for lift, points in series.items()
        }
    )


@router.get("/readiness", response_model=ReadinessOut)
@limiter.limit("60/minute")
def get_readiness(
    request: Request,
    date_: date = Query(default_factory=date.today, alias="date"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> ReadinessOut:
    """The 0-100 readiness composite for a date, with its contributing factors
    (PRD §2.4). Computed on demand from the most recent wearable samples."""
    profile = _get_profile(db, user)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No athlete profile yet")
    # 31-day window: baseline needs 30 days, plus the target day itself.
    lo = datetime.combine(date_ - timedelta(days=31), time.min, tzinfo=UTC)
    hi = datetime.combine(date_ + timedelta(days=1), time.min, tzinfo=UTC)
    samples = db.scalars(
        select(WearableSample).where(
            WearableSample.athlete_id == profile.id,
            WearableSample.occurred_at >= lo,
            WearableSample.occurred_at < hi,
        )
    ).all()
    result = compute_readiness(list(samples), date_)
    return ReadinessOut(
        date=date_,
        score=result.score,
        band=result.band,
        guidance=result.guidance,
        factors=[
            ReadinessFactorOut(
                key=f.key, label=f.label, value=f.value, score=f.score, weight=f.weight
            )
            for f in result.factors
        ],
    )
