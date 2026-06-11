"""Notification routes (PRD §2.3): APNs device registration + preferences."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.auth.clerk import require_user
from obelisk_api.db.base import get_db
from obelisk_api.db.models import AthleteProfile, User
from obelisk_api.domain.schemas import (
    DeviceTokenIn,
    NotificationPrefsIn,
    NotificationPrefsOut,
)
from obelisk_api.ratelimit import limiter

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _profile_or_404(db: Session, user: User) -> AthleteProfile:
    profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No athlete profile yet")
    return profile


def _prefs_out(profile: AthleteProfile) -> NotificationPrefsOut:
    return NotificationPrefsOut(
        morning_ping_enabled=profile.morning_ping_enabled,
        morning_ping_time=profile.morning_ping_time,
        weekly_recap_enabled=profile.weekly_recap_enabled,
        event_notifications_enabled=profile.event_notifications_enabled,
        quiet_hours_start=profile.quiet_hours_start,
        quiet_hours_end=profile.quiet_hours_end,
        timezone=profile.timezone,
        device_registered=bool(profile.apns_device_token),
    )


@router.post("/register", response_model=NotificationPrefsOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
def register_device(
    request: Request,
    payload: DeviceTokenIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> NotificationPrefsOut:
    """Store the athlete's APNs device token (treated like a credential — never
    echoed back; we only report whether one is set)."""
    profile = _profile_or_404(db, user)
    profile.apns_device_token = payload.device_token
    db.flush()
    return _prefs_out(profile)


@router.get("/preferences", response_model=NotificationPrefsOut)
@limiter.limit("60/minute")
def get_preferences(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> NotificationPrefsOut:
    return _prefs_out(_profile_or_404(db, user))


@router.patch("/preferences", response_model=NotificationPrefsOut)
@limiter.limit("30/minute")
def update_preferences(
    request: Request,
    payload: NotificationPrefsIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> NotificationPrefsOut:
    profile = _profile_or_404(db, user)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(profile, field, value)
    db.flush()
    return _prefs_out(profile)
