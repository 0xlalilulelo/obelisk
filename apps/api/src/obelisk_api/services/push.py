"""Push notifications (PRD §2.3). The dispatch *policy* (quiet hours, one-per-day,
defer-if-unopened) and *content* are pure and unit-tested; the APNs transport is
gated on config and is a no-op when unconfigured.

Every notification ties to a number that changed (PRD §6.6) — the content builders
take that number as an argument rather than inventing encouragement.
"""

from __future__ import annotations

from datetime import datetime, timedelta


def _mins(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def in_quiet_hours(now_hhmm: str, start: str, end: str) -> bool:
    """Whether ``now`` falls in the quiet window. Handles a window that wraps
    midnight (the default 22:00–06:00)."""
    n, s, e = _mins(now_hhmm), _mins(start), _mins(end)
    if s == e:
        return False
    if s < e:
        return s <= n < e
    return n >= s or n < e  # wraps midnight


def should_send_morning(
    *,
    enabled: bool,
    now_hhmm: str,
    quiet_start: str,
    quiet_end: str,
    last_sent: datetime | None,
    last_opened: datetime | None,
    now: datetime,
) -> bool:
    """One morning ping per day, never in quiet hours, and deferred 24h if the
    previous notification went unopened (anti-spam, PRD §2.3)."""
    if not enabled:
        return False
    if in_quiet_hours(now_hhmm, quiet_start, quiet_end):
        return False
    if last_sent is not None:
        if last_sent.date() == now.date():
            return False  # already sent today
        if last_opened is None and now - last_sent < timedelta(hours=24):
            return False  # previous went unopened — back off
    return True


def morning_ping_content(
    session_title: str, readiness: int | None, insight: str | None
) -> tuple[str, str]:
    title = f"Today: {session_title}"
    parts: list[str] = []
    if readiness is not None:
        parts.append(f"Readiness {readiness}.")
    if insight:
        parts.append(insight)
    return title, " ".join(parts) if parts else "Your session is ready."


def weekly_recap_content(
    completed: int, prescribed: int, notable: str, monday_session: str
) -> tuple[str, str]:
    title = f"Week recap: {completed}/{prescribed} sessions"
    body = f"Notable: {notable}. Next week starts with {monday_session}."
    return title, body


async def send_push(
    device_token: str | None, title: str, body: str, *, badge: int | None = None
) -> bool:
    """Send one APNs alert. Returns False (no-op) when APNs or the token is
    unconfigured — never raises into the caller."""
    from obelisk_api.config import get_settings

    settings = get_settings()
    if not (
        device_token
        and settings.apns_key_id
        and settings.apns_team_id
        and settings.apns_private_key
    ):
        return False

    from aioapns import APNs, NotificationRequest

    apns = APNs(
        key=settings.apns_private_key,
        key_id=settings.apns_key_id,
        team_id=settings.apns_team_id,
        topic=settings.apns_topic,
        use_sandbox=settings.apns_use_sandbox,
    )
    alert: dict[str, object] = {"title": title, "body": body}
    aps: dict[str, object] = {"alert": alert, "sound": "default"}
    if badge is not None:
        aps["badge"] = badge
    request = NotificationRequest(device_token=device_token, message={"aps": aps})
    response = await apns.send_notification(request)
    return bool(getattr(response, "is_successful", False))


def now_hhmm(dt: datetime) -> str:
    return dt.strftime("%H:%M")
