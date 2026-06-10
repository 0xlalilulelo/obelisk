"""Apple StoreKit 2 transaction handling (PRD §2.6).

A StoreKit 2 signed transaction is a JWS whose header carries Apple's x5c cert
chain. Production must verify that chain against Apple's root CA (gated by
``apple_storekit_verification``); until that's wired we decode the payload only,
which is fine for dev/TestFlight against the sandbox but is **not** trustworthy in
production. The endpoint refuses to run verification-on without a verifier so we
never silently trust an unverified receipt in prod.
"""

from __future__ import annotations

from typing import Any

import jwt

from obelisk_api.config import get_settings


class AppleVerificationUnavailableError(RuntimeError):
    """Raised when verification is required (production) but not yet implemented."""


def decode_transaction(signed_transaction: str) -> dict[str, Any]:
    """Return the transaction payload. Verifies the signature chain when
    ``apple_storekit_verification`` is on; otherwise decodes without verifying."""
    settings = get_settings()
    if settings.apple_storekit_verification:
        # The x5c-chain verification path needs Apple's root certs + the
        # app-store-server-library. Not wired yet — fail loudly rather than
        # pretend a receipt is verified.
        raise AppleVerificationUnavailableError(
            "Apple StoreKit signature verification is enabled but not configured."
        )
    return jwt.decode(
        signed_transaction,
        options={"verify_signature": False, "verify_aud": False, "verify_exp": False},
    )
