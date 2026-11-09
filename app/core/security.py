"""Mock demo authentication and role checks.

There is no real login: the caller names a seeded demo user in the `X-Demo-User`
header. Every server-side authorization decision goes through this module.
"""

from collections.abc import Callable, Collection
from enum import StrEnum

from app.core.errors import AppError, ErrorCode
from app.db.models import AppUser, Status

DEMO_USER_HEADER = "X-Demo-User"


class RoleCode(StrEnum):
    DATA_SUBMITTER = "DATA_SUBMITTER"
    DATA_STEWARD = "DATA_STEWARD"
    PLATFORM_ADMIN = "PLATFORM_ADMIN"
    SECURITY_REVIEWER = "SECURITY_REVIEWER"
    DATA_CONSUMER = "DATA_CONSUMER"


def authenticate_demo_user(
    username: str | None, find_user: Callable[[str], AppUser | None]
) -> AppUser:
    """Resolve the `X-Demo-User` header value to an active user, or raise a 401."""
    username = (username or "").strip()
    if not username:
        raise AppError(
            401,
            ErrorCode.DEMO_USER_HEADER_MISSING,
            f"Select a demo user: send the {DEMO_USER_HEADER} header.",
        )
    user = find_user(username)
    if user is None:
        raise AppError(401, ErrorCode.DEMO_USER_UNKNOWN, "Unknown demo user.")
    if user.status != Status.ACTIVE:
        raise AppError(401, ErrorCode.DEMO_USER_INACTIVE, "This demo user is inactive.")
    return user


def ensure_any_role(user: AppUser, allowed: Collection[RoleCode]) -> None:
    """Raise a 403 unless the user holds at least one of the allowed roles."""
    if user.role_codes.isdisjoint(allowed):
        raise AppError(
            403, ErrorCode.FORBIDDEN, "Your demo role is not allowed to perform this action."
        )
