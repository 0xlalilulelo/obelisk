"""SQLAlchemy engine, session factory, and declarative base.

Sync SQLAlchemy 2.0: FastAPI runs sync route handlers in a threadpool, so a sync
Session is the simplest correct choice for Phase 1 (chat is synchronous request/
response — no background jobs).
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from obelisk_api.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_settings = get_settings()
# pool_pre_ping avoids stale connections after Postgres idle timeouts.
engine = create_engine(_settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session, committed/rolled back per request."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
