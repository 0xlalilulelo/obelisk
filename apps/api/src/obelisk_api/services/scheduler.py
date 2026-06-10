"""In-process notification scheduler (APScheduler, PRD §2.3).

Disabled by default (``push_scheduler_enabled``). When on, it runs an hourly
morning tick and a Sunday-evening recap tick. Content + quiet-hours come from the
unit-tested helpers in ``push``.

Known Phase-3 follow-ups before enabling in production: durable per-athlete
send-state (``last_morning_sent_at`` / ``last_opened_at`` columns) so the
one-per-day / defer-if-unopened rules survive restarts, and timezone-correct
local-time scheduling (this tick compares against UTC).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.config import get_settings
from obelisk_api.db.base import SessionLocal
from obelisk_api.db.models import AthleteProfile, Block, WearableSample
from obelisk_api.domain.models import CyclePlan
from obelisk_api.services import push, readiness
from obelisk_api.services.session import expand_session

_scheduler = None


def start() -> object | None:
    """Start the scheduler if enabled. Returns the scheduler (or None)."""
    global _scheduler
    if not get_settings().push_scheduler_enabled or _scheduler is not None:
        return _scheduler
    from apscheduler.schedulers.asyncio import (  # type: ignore[import-untyped]
        AsyncIOScheduler,
    )

    sched = AsyncIOScheduler(timezone="UTC")
    sched.add_job(morning_tick, "cron", minute=0, id="morning_ping")
    sched.add_job(weekly_tick, "cron", day_of_week="sun", hour=18, id="weekly_recap")
    sched.start()
    _scheduler = sched
    return sched  # type: ignore[no-any-return]


async def morning_tick() -> int:
    """Send the morning ping to athletes whose configured hour matches now and who
    aren't in quiet hours. Returns the number sent (best-effort)."""
    now = datetime.now(UTC)
    hhmm = push.now_hhmm(now)
    sent = 0
    db = SessionLocal()
    try:
        profiles = db.scalars(
            select(AthleteProfile)
            .where(AthleteProfile.morning_ping_enabled)
            .where(AthleteProfile.apns_device_token.is_not(None))
        ).all()
        for p in profiles:
            if hhmm[:2] != p.morning_ping_time[:2]:
                continue
            if push.in_quiet_hours(hhmm, p.quiet_hours_start, p.quiet_hours_end):
                continue
            title, body = _morning_for(db, p, now.date())
            if await push.send_push(p.apns_device_token, title, body):
                sent += 1
    finally:
        db.close()
    return sent


async def weekly_tick() -> int:
    """Stub recap dispatch — full weekly stats land with the recap query (§6.3)."""
    return 0


def _morning_for(db: Session, profile: AthleteProfile, today: date) -> tuple[str, str]:
    """Build the morning content: today's session title + readiness number."""
    session_title = "Training day"
    block = db.scalar(select(Block).where(Block.athlete_id == profile.id, Block.phase == "active"))
    if block and block.plan_json and block.start_date:
        try:
            plan = CyclePlan.model_validate(block.plan_json)
            session = expand_session(plan, str(block.id), block.start_date, today)
            session_title = session.session_title
        except Exception:  # a malformed plan must not block the tick
            pass
    score = readiness.compute_readiness(_recent_samples(db, profile.id, today), today).score
    return push.morning_ping_content(session_title, score, None)


def _recent_samples(db: Session, athlete_id: uuid.UUID, today: date) -> list[WearableSample]:
    lo = datetime.combine(today - timedelta(days=31), time.min, tzinfo=UTC)
    return list(
        db.scalars(
            select(WearableSample).where(
                WearableSample.athlete_id == athlete_id,
                WearableSample.occurred_at >= lo,
            )
        ).all()
    )
