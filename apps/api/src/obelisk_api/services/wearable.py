"""HealthKit sample ingest (PRD §2.2). Deduplicated on (athlete, source,
sample_uuid) so re-syncing HealthKit's rolling window is a no-op. Samples are
PHI-adjacent: nothing here logs raw values to stdout / Sentry.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.db.models import WearableSample
from obelisk_api.domain.schemas import WearableSampleIn


def _dedup_key(athlete_id: uuid.UUID, source: str, sample_uuid: str) -> str:
    return f"{athlete_id}:{source}:{sample_uuid}"


def ingest_samples(
    db: Session, athlete_id: uuid.UUID, samples: list[WearableSampleIn]
) -> tuple[int, int]:
    """Persist a batch, skipping samples already stored. Returns (inserted, duplicates)."""
    keys = [_dedup_key(athlete_id, s.source, s.sample_uuid) for s in samples]
    existing = set(
        db.scalars(select(WearableSample.dedup_key).where(WearableSample.dedup_key.in_(keys))).all()
    )
    inserted = 0
    duplicates = 0
    seen: set[str] = set()
    for s, key in zip(samples, keys, strict=True):
        if key in existing or key in seen:
            duplicates += 1
            continue
        seen.add(key)
        db.add(
            WearableSample(
                athlete_id=athlete_id,
                source=s.source,
                sample_type=s.sample_type,
                occurred_at=s.occurred_at,
                duration_sec=s.duration_sec,
                value=s.value,
                unit=s.unit,
                raw=s.raw,
                dedup_key=key,
            )
        )
        inserted += 1
    db.flush()
    return inserted, duplicates
