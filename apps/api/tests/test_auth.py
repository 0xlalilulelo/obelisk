"""Unit tests for the Clerk verifier's issuer handling (no network)."""

from __future__ import annotations

import pytest

from obelisk_api.auth.clerk import ClerkVerifier

BASE = "https://apparent-wahoo-59.clerk.accounts.dev"


@pytest.mark.parametrize(
    "given",
    [
        BASE,
        BASE + "/",
        BASE + "/.well-known/jwks.json",  # the easy-to-paste-wrong form
    ],
)
def test_issuer_normalizes_to_base(given: str) -> None:
    v = ClerkVerifier(given, audience=None)
    assert v._issuer == BASE
    # The JWKS client is always pointed at the single canonical endpoint.
    assert v._jwk_client.uri == f"{BASE}/.well-known/jwks.json"
