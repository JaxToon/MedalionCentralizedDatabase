"""User queries. Users are always loaded with their unit and roles."""

from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.db.models import AppUser, Status


def _users_with_unit_and_roles() -> Select[tuple[AppUser]]:
    return select(AppUser).options(joinedload(AppUser.unit), selectinload(AppUser.roles))


def get_user_by_username(session: Session, username: str) -> AppUser | None:
    return session.scalar(_users_with_unit_and_roles().where(AppUser.username == username))


def list_active_users(session: Session) -> Sequence[AppUser]:
    return session.scalars(
        _users_with_unit_and_roles()
        .where(AppUser.status == Status.ACTIVE)
        .order_by(AppUser.display_name)
    ).all()
