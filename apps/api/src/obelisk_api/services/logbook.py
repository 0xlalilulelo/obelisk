"""Set-log persistence + read helpers for the In-Session surface (PRD §2.1).

The on-device queue flushes batches to ``POST /v1/log``. Each set carries a
device-generated UUID that becomes the ``LogEntry`` primary key, so a retry after
a dropped connection (the gym-basement case) inserts the same row id and is a
no-op rather than a duplicate. Reads here back the pre-fill (prior session's
actuals) and the e1RM used for haptic PR detection.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.db.models import LogEntry
from obelisk_api.domain.schemas import SetLogIn
from obelisk_api.tools.deterministic import compute_1rm

# How many recent set rows to scan for pre-fill / PR. A beta athlete logs well
# under this per cycle; scanning in Python keeps the query dialect-portable
# (SQLite in tests, JSONB in prod) without per-dialect JSON path operators.
_SCAN_LIMIT = 1000


def insert_set_logs(db: Session, athlete_id: uuid.UUID, sets: list[SetLogIn]) -> tuple[int, int]:
    """Idempotently persist a batch. Returns (inserted, duplicates).

    Idempotency key is ``SetLogIn.client_id`` (used as the row PK). Rows whose id
    already exists for this athlete are skipped. A client_id that collides with a
    different athlete's row is also skipped — we never overwrite an existing row.
    """
    ids = [s.client_id for s in sets]
    existing = set(db.scalars(select(LogEntry.id).where(LogEntry.id.in_(ids))).all())
    inserted = 0
    duplicates = 0
    seen: set[uuid.UUID] = set()
    for s in sets:
        if s.client_id in existing or s.client_id in seen:
            duplicates += 1
            continue
        seen.add(s.client_id)
        db.add(
            LogEntry(
                id=s.client_id,
                athlete_id=athlete_id,
                type="set",
                occurred_at=s.occurred_at or datetime.now(UTC),
                source="ios",
                data={
                    "block_id": str(s.block_id) if s.block_id else None,
                    "session_date": s.session_date.isoformat(),
                    "exercise": s.exercise,
                    "lift_key": s.lift_key,
                    "set_index": s.set_index,
                    "weight_lb": s.weight_lb,
                    "reps": s.reps,
                    "rpe": s.rpe,
                    "completed": s.completed,
                },
            )
        )
        inserted += 1
    db.flush()
    return inserted, duplicates


def _set_rows(db: Session, athlete_id: uuid.UUID) -> list[LogEntry]:
    return list(
        db.scalars(
            select(LogEntry)
            .where(LogEntry.athlete_id == athlete_id, LogEntry.type == "set")
            .order_by(LogEntry.occurred_at.desc())
            .limit(_SCAN_LIMIT)
        ).all()
    )


def _matches(data: dict[str, Any], lift_key: str | None, label: str) -> bool:
    """Same identity rule as PrescribedExercise.match_key: canonical lift key when
    present, otherwise the exercise label."""
    if lift_key:
        return data.get("lift_key") == lift_key
    return data.get("exercise") == label


def prior_actuals(
    db: Session,
    athlete_id: uuid.UUID,
    lift_key: str | None,
    label: str,
    before: date,
) -> list[dict[str, Any]]:
    """The most recent session (strictly before ``before``) that logged this
    exercise, returned as its sets ordered by set_index — the pre-fill source."""
    rows = [
        r
        for r in _set_rows(db, athlete_id)
        if _matches(r.data, lift_key, label) and r.data.get("session_date", "") < before.isoformat()
    ]
    if not rows:
        return []
    latest_date = max(r.data["session_date"] for r in rows)
    sets = [r for r in rows if r.data["session_date"] == latest_date]
    sets.sort(key=lambda r: r.data.get("set_index", 0))
    return [
        {
            "set_index": r.data.get("set_index", 0),
            "weight_lb": r.data.get("weight_lb", 0.0),
            "reps": r.data.get("reps", 0),
            "rpe": r.data.get("rpe"),
            "occurred_at": r.occurred_at,
        }
        for r in sets
    ]


def best_e1rm(db: Session, athlete_id: uuid.UUID, lift_key: str) -> dict[str, Any] | None:
    """Highest Epley e1RM across all logged sets for a lift, with the set that
    produced it. None when the athlete has never logged the lift."""
    best: dict[str, Any] | None = None
    for r in _set_rows(db, athlete_id):
        if r.data.get("lift_key") != lift_key:
            continue
        weight = r.data.get("weight_lb") or 0
        reps = r.data.get("reps") or 0
        if weight <= 0 or reps < 1:
            continue
        e1rm = compute_1rm(weight, reps)
        if best is None or e1rm > best["e1rm"]:
            best = {
                "e1rm": e1rm,
                "weight_lb": weight,
                "reps": reps,
                "occurred_at": r.occurred_at,
            }
    return best


def e1rm_series(db: Session, athlete_id: uuid.UUID) -> dict[str, list[dict[str, Any]]]:
    """Per-lift best-e1RM-per-day time series for the analytics charts (PRD §2.7).

    Keyed by lift_key; each value is a date-sorted list of ``{date, e1rm}`` where
    e1rm is the best Epley estimate logged that calendar day."""
    # (lift_key, date) -> best e1rm that day
    best_by_day: dict[tuple[str, str], int] = {}
    for r in _set_rows(db, athlete_id):
        lift = r.data.get("lift_key")
        if not lift:
            continue
        weight = r.data.get("weight_lb") or 0
        reps = r.data.get("reps") or 0
        if weight <= 0 or reps < 1:
            continue
        day = r.data.get("session_date") or r.occurred_at.date().isoformat()
        e1rm = compute_1rm(weight, reps)
        key = (lift, day)
        if key not in best_by_day or e1rm > best_by_day[key]:
            best_by_day[key] = e1rm

    series: dict[str, list[dict[str, Any]]] = {}
    for (lift, day), e1rm in best_by_day.items():
        series.setdefault(lift, []).append({"date": day, "e1rm": e1rm})
    for points in series.values():
        points.sort(key=lambda p: p["date"])
    return series
