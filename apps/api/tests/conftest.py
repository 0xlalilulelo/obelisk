"""Shared fixtures for API route tests.

Everything external is faked: SQLite (not Postgres), injected Clerk claims (no live
token exchange — ADR-004), and a fake Anthropic client (no network). This keeps
api.yml CI green without secrets or services.
"""

from __future__ import annotations

import os

# Unit tests exercise route contracts, not throughput — disable per-user rate
# limiting so a fast-looping test can't trip the limiter. Set before app import.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from obelisk_api.auth.clerk import get_token_claims
from obelisk_api.db.base import Base, get_db
from obelisk_api.deps import get_anthropic_client
from obelisk_api.main import create_app


# --- Fake Anthropic client -------------------------------------------------
def usage(in_t: int = 2000, out_t: int = 120) -> SimpleNamespace:
    return SimpleNamespace(
        input_tokens=in_t,
        output_tokens=out_t,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
    )


def text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def tool_use_block(name: str, tool_id: str, tool_input: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", name=name, id=tool_id, input=tool_input)


def end_turn(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[text_block(text)], stop_reason="end_turn", usage=usage())


class FakeMessages:
    def __init__(self, responses: list[SimpleNamespace]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        if self._responses:
            return self._responses.pop(0)
        return end_turn("Acknowledged.")  # default when the script runs out


class FakeAnthropic:
    """Mimics anthropic.Anthropic for the agent loop; scriptable per test."""

    def __init__(self, responses: list[SimpleNamespace] | None = None) -> None:
        self.messages = FakeMessages(responses or [])

    def queue(self, *responses: SimpleNamespace) -> None:
        self.messages._responses.extend(responses)


def draft_then_explain() -> list[SimpleNamespace]:
    """A hybrid_531 draft turn: call draft_cycle_plan, then explain."""
    return [
        SimpleNamespace(
            content=[
                tool_use_block(
                    "draft_cycle_plan",
                    "tu1",
                    {
                        "program_model": "hybrid_531",
                        "title": "Crucible-25",
                        "goals": ["aerobic base + submaximal strength"],
                        "priority_lifts": ["bench_press"],
                    },
                )
            ],
            stop_reason="tool_use",
            usage=usage(),
        ),
        end_turn("Drafted your cycle. TMs at 85% of 1RM per the Brief."),
    ]


# --- App / client fixtures -------------------------------------------------
@pytest.fixture
def engine() -> Iterator[Any]:
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture
def session_factory(engine: Any) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


@pytest.fixture
def fake_anthropic() -> FakeAnthropic:
    return FakeAnthropic()


@pytest.fixture
def client(
    session_factory: sessionmaker[Session], fake_anthropic: FakeAnthropic
) -> Iterator[tuple[TestClient, Callable[[str], None]]]:
    """Authenticated client. Returns (client, set_user) — set_user switches identity."""
    app = create_app()
    claims: dict[str, Any] = {"sub": "user_a", "email": "a@example.com"}

    def override_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_token_claims] = lambda: claims
    app.dependency_overrides[get_anthropic_client] = lambda: fake_anthropic

    def set_user(sub: str) -> None:
        claims["sub"] = sub
        claims["email"] = f"{sub}@example.com"

    with TestClient(app) as test_client:
        yield test_client, set_user


@pytest.fixture
def raw_client(session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    """Client WITHOUT the auth override — for testing 401s."""
    app = create_app()

    def override_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
            db.commit()
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client


JOSH_PROFILE = {
    "name": "Josh",
    "age": 34,
    "sex": "male",
    "bodyweight_lb": 175,
    "height_in": 74,
    "resting_hr_bpm": 59,
    "estimated_1rm": {
        "back_squat": 259,
        "deadlift": 336,
        "bench_press": 182,
        "strict_press": 123,
        "front_squat": 248,
        "power_clean": 182,
    },
    "primary_goals": ["bench priority", "finger strength"],
    "equipment": "full_gym",
    "days_per_week": 6,
    "primary_modality": "hybrid",
}
