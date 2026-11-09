"""Reusable FastAPI dependencies: database session, current demo user, role checks."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.security import DEMO_USER_HEADER, RoleCode, authenticate_demo_user, ensure_any_role
from app.db.models import AppUser
from app.db.repositories import users
from app.db.session import get_session

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_user(
    request: Request,
    session: SessionDep,
    demo_user: Annotated[str | None, Header(alias=DEMO_USER_HEADER)] = None,
) -> AppUser:
    user = authenticate_demo_user(
        demo_user, lambda username: users.get_user_by_username(session, username)
    )
    # Read by the request logging middleware so every request log carries the actor.
    request.state.actor_id = str(user.user_id)
    return user


CurrentUser = Annotated[AppUser, Depends(get_current_user)]


def require_roles(*roles: RoleCode) -> Callable[[AppUser], AppUser]:
    """Dependency factory: `Depends(require_roles(RoleCode.PLATFORM_ADMIN, ...))`.

    Resolves the current user and raises 403 unless they hold one of `roles`.
    """
    if not roles:
        raise ValueError("require_roles() needs at least one role")
    allowed = frozenset(roles)

    def check(user: CurrentUser) -> AppUser:
        ensure_any_role(user, allowed)
        return user

    return check
