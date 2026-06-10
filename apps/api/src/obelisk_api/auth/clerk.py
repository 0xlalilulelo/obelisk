"""Clerk JWT authentication (ADR-004).

Clerk is the identity source of truth. Every /v1 request (except /healthz) carries
a Clerk session JWT as a Bearer token; we verify it against Clerk's JWKS, extract
the user id, and upsert a local ``User`` mirror. We never build custom auth.

Testability: the verification seam is the ``get_token_claims`` dependency, which
tests override with a fake — so route tests assert the contract without a live Clerk.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from obelisk_api.config import Settings, get_settings
from obelisk_api.db.base import get_db
from obelisk_api.db.models import User

_bearer = HTTPBearer(auto_error=False)


class ClerkVerifier:
    """Verifies Clerk-issued RS256 JWTs against the issuer's JWKS (cached by PyJWT)."""

    _JWKS_SUFFIX = "/.well-known/jwks.json"

    def __init__(self, issuer: str, audience: str | None) -> None:
        # Accept either the base issuer (https://app.clerk.accounts.dev) or a full
        # JWKS URL — Clerk's dashboard surfaces both. Normalize to the base issuer so
        # the `iss` claim check and the JWKS URL are both correct.
        normalized = issuer.strip().rstrip("/")
        if normalized.endswith(self._JWKS_SUFFIX):
            normalized = normalized[: -len(self._JWKS_SUFFIX)]
        self._issuer = normalized
        self._audience = audience
        self._jwk_client = jwt.PyJWKClient(f"{self._issuer}{self._JWKS_SUFFIX}")

    def verify(self, token: str) -> dict[str, Any]:
        signing_key = self._jwk_client.get_signing_key_from_jwt(token)
        claims: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=self._issuer,
            audience=self._audience,
            options={"verify_aud": self._audience is not None},
        )
        return claims


@lru_cache(maxsize=1)
def get_verifier() -> ClerkVerifier:
    settings = get_settings()
    if not settings.clerk_issuer:
        raise RuntimeError("CLERK_ISSUER is not configured; cannot verify auth tokens.")
    return ClerkVerifier(settings.clerk_issuer, settings.clerk_audience)


def _dev_claims_or_none(token: str) -> dict[str, Any] | None:
    """Synthetic claims for the dev-auth escape hatch. Active only when
    ``dev_auth_token`` is configured and we're not in production."""
    settings = get_settings()
    if not settings.dev_auth_token or settings.environment == "production":
        return None
    if token != settings.dev_auth_token:
        return None
    return {"sub": settings.dev_auth_sub, "email": f"{settings.dev_auth_sub}@obelisk.test"}


def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """Verify the Bearer token and return its claims. Override in tests."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    dev_claims = _dev_claims_or_none(credentials.credentials)
    if dev_claims is not None:
        return dev_claims
    try:
        return get_verifier().verify(credentials.credentials)
    except Exception as exc:  # pyjwt raises a family of errors; all mean "unauthorized"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc


def require_user(
    request: Request,
    claims: dict[str, Any] = Depends(get_token_claims),
    db: Session = Depends(get_db),
) -> User:
    """Resolve (and upsert on first sight) the local User for the verified token."""
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject"
        )
    user = db.scalar(select(User).where(User.clerk_user_id == clerk_user_id))
    if user is None:
        email = claims.get("email") or claims.get("email_address") or ""
        user = User(clerk_user_id=clerk_user_id, email=email)
        db.add(user)
        db.flush()  # assign PK without ending the request transaction
    # Stash the user id so the slowapi key_func can rate-limit per athlete.
    request.state.rate_limit_user = str(user.id)
    return user


__all__ = ["ClerkVerifier", "Settings", "get_token_claims", "get_verifier", "require_user"]
