"""Block (session) state and JSON-file persistence under ``runs/<id>/``.

A Block is the unit of work (PRD §5): a self-contained cycle with its own
athlete profile, durable plan artifact, pending change, and conversation. No
database — everything is JSON files plus the rendered xlsx.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from obelisk_api.domain.models import Athlete, CyclePlan, PlanDiff

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"

# A conversation message is a JSON-able dict: {"role": ..., "content": ...}.
Message = dict[str, object]


def new_block_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%d-%H%M%S")


@dataclass
class Block:
    """Mutable session state for one training Block."""

    block_id: str
    model: str
    athlete: Athlete
    name: str = "Untitled Block"
    current_plan: CyclePlan | None = None
    pending_plan: CyclePlan | None = None
    last_diff: PlanDiff | None = None
    messages: list[Message] = field(default_factory=list)

    @property
    def run_dir(self) -> Path:
        return RUNS_DIR / self.block_id

    @property
    def xlsx_path(self) -> Path:
        return self.run_dir / "cycle_plan.xlsx"

    def save(self) -> None:
        """Persist block metadata, plan, and conversation to ``runs/<id>/``."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, object] = {
            "block_id": self.block_id,
            "name": self.name,
            "model": self.model,
            "athlete": self.athlete.model_dump(),
            "current_plan": self.current_plan.model_dump() if self.current_plan else None,
            "messages": self.messages,
        }
        (self.run_dir / "block.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if self.current_plan is not None:
            (self.run_dir / "plan.json").write_text(
                self.current_plan.model_dump_json(indent=2), encoding="utf-8"
            )

    @classmethod
    def load(cls, block_id: str) -> Block:
        """Load a Block by id from ``runs/<id>/block.json``."""
        path = RUNS_DIR / block_id / "block.json"
        if not path.exists():
            raise FileNotFoundError(f"No Block found at {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        plan_data = data.get("current_plan")
        return cls(
            block_id=data["block_id"],
            model=data["model"],
            name=data.get("name", "Untitled Block"),
            athlete=Athlete.model_validate(data["athlete"]),
            current_plan=CyclePlan.model_validate(plan_data) if plan_data else None,
            messages=list(data.get("messages", [])),
        )


def list_blocks() -> list[str]:
    """Return known block ids, newest first."""
    if not RUNS_DIR.exists():
        return []
    return sorted((p.name for p in RUNS_DIR.iterdir() if (p / "block.json").exists()), reverse=True)
