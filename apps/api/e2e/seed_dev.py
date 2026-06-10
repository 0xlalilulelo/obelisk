"""Seed a dev athlete + block for local E2E, paired with the dev-auth token.

Idempotent: re-running reuses the existing dev user / profile / block. The block
gets a deterministic plan (no LLM) so `GET /v1/blocks/{id}/sessions/{date}` works.

    DATABASE_URL=postgresql+psycopg://obelisk:obelisk@localhost:55432/obelisk \
        uv run python e2e/seed_dev.py
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from obelisk_api.db.base import SessionLocal
from obelisk_api.db.models import AthleteProfile, Block, User
from obelisk_api.domain.models import Athlete, EstimatedOneRepMax
from obelisk_api.services.planbuilder import build_default_plan

DEV_SUB = "dev_user"
ONE_RM = {
    "back_squat": 259,
    "deadlift": 336,
    "bench_press": 182,
    "strict_press": 123,
    "front_squat": 248,
    "power_clean": 182,
}


def main() -> None:
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.clerk_user_id == DEV_SUB))
        if user is None:
            user = User(clerk_user_id=DEV_SUB, email=f"{DEV_SUB}@obelisk.test")
            db.add(user)
            db.flush()

        profile = db.scalar(select(AthleteProfile).where(AthleteProfile.user_id == user.id))
        if profile is None:
            profile = AthleteProfile(
                user_id=user.id,
                name="Dev Athlete",
                age=34,
                sex="male",
                bodyweight_lb=175,
                height_in=74,
                resting_hr_bpm=59,
                estimated_1rm=ONE_RM,
                primary_goals=["bench priority", "finger strength"],
                equipment="full_gym",
                days_per_week=6,
                primary_modality="hybrid",
            )
            db.add(profile)
            db.flush()

        block = db.scalar(select(Block).where(Block.athlete_id == profile.id))
        if block is None:
            athlete = Athlete(
                name=profile.name,
                age=profile.age,
                bodyweight_lb=profile.bodyweight_lb or 175,
                height_in=profile.height_in,
                estimated_1rm=EstimatedOneRepMax(**ONE_RM),
                primary_goals=list(profile.primary_goals),
            )
            plan = build_default_plan(
                athlete,
                title="Dev Cycle — local E2E",
                goals=["Bench priority", "Maintain squat/DL", "MAF aerobic base"],
                priority_lifts=["bench_press"],
            )
            total_weeks = len(plan.waves) * 4
            block = Block(
                athlete_id=profile.id,
                name="Dev Block",
                goal="local e2e",
                program_model="hybrid_531",
                start_date=date.today(),
                end_date=date.today() + timedelta(weeks=total_weeks),
                plan_json=plan.model_dump(),
            )
            db.add(block)
            db.flush()

        db.commit()
        print(f"user={user.id} profile={profile.id} block={block.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
