"""Shared FastAPI dependencies (injectable seams for tests)."""

from __future__ import annotations

from anthropic import Anthropic

from obelisk_api.agent.loop import require_client


def get_anthropic_client() -> Anthropic:
    """The Anthropic client. Overridden in tests with a fake (no network)."""
    return require_client()
