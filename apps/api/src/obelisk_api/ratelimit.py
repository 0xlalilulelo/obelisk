"""Per-user rate limiting (slowapi) for the /v1 surface (PRD §2 security checklist).

A single module-level ``limiter`` is shared across routers. It keys on the
authenticated user id (stashed on ``request.state`` by ``require_user``) so limits
are per-athlete, not per-IP — a gym Wi-Fi NAT shouldn't make one athlete's logging
throttle another's. Enable/disable is flipped in ``create_app`` from settings so
the unit-test app can turn it off.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


def user_key(request: Request) -> str:
    """Rate-limit bucket: authenticated user id, then bearer token, then client IP."""
    uid = getattr(request.state, "rate_limit_user", None)
    if uid:
        return str(uid)
    auth = request.headers.get("authorization")
    if auth:
        return auth
    return get_remote_address(request)


limiter = Limiter(key_func=user_key, default_limits=[])
