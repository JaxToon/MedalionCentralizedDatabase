"""PostgreSQL itself rejects duplicate identity rows and dangling references."""

import uuid

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AppUser, OrganizationUnit, Role, UserRole


def add_unit(session: Session, code: str = "UNIT_A") -> uuid.UUID:
    return session.scalar(
        insert(OrganizationUnit)
        .values(unit_code=code, unit_name=f"Unit {code}")
        .returning(OrganizationUnit.unit_id)
    )


def add_role(session: Session, code: str = "ROLE_A") -> uuid.UUID:
    return session.scalar(
        insert(Role).values(role_code=code, role_name=f"Role {code}").returning(Role.role_id)
    )


def add_user(session: Session, unit_id: uuid.UUID, username: str, email: str) -> uuid.UUID:
    return session.scalar(
        insert(AppUser)
        .values(unit_id=unit_id, username=username, email=email, display_name=username)
        .returning(AppUser.user_id)
    )


def duplicate_unit_code(session: Session) -> None:
    add_unit(session, "DUP")
    add_unit(session, "DUP")


def duplicate_role_code(session: Session) -> None:
    add_role(session, "DUP")
    add_role(session, "DUP")


def duplicate_username(session: Session) -> None:
    unit_id = add_unit(session)
    add_user(session, unit_id, "same.name", "one@demo.local")
    add_user(session, unit_id, "same.name", "two@demo.local")


def duplicate_email(session: Session) -> None:
    unit_id = add_unit(session)
    add_user(session, unit_id, "user.one", "same@demo.local")
    add_user(session, unit_id, "user.two", "same@demo.local")


def duplicate_user_role(session: Session) -> None:
    user_id = add_user(session, add_unit(session), "user.one", "one@demo.local")
    role_id = add_role(session)
    session.execute(insert(UserRole).values(user_id=user_id, role_id=role_id))
    session.execute(insert(UserRole).values(user_id=user_id, role_id=role_id))


def user_with_unknown_unit(session: Session) -> None:
    add_user(session, uuid.uuid4(), "orphan", "orphan@demo.local")


def assignment_with_unknown_role(session: Session) -> None:
    user_id = add_user(session, add_unit(session), "user.one", "one@demo.local")
    session.execute(insert(UserRole).values(user_id=user_id, role_id=uuid.uuid4()))


def assignment_by_unknown_assigner(session: Session) -> None:
    user_id = add_user(session, add_unit(session), "user.one", "one@demo.local")
    session.execute(
        insert(UserRole).values(user_id=user_id, role_id=add_role(session), assigned_by=uuid.uuid4())
    )


@pytest.mark.parametrize(
    "violation",
    [
        duplicate_unit_code,
        duplicate_role_code,
        duplicate_username,
        duplicate_email,
        duplicate_user_role,
        user_with_unknown_unit,
        assignment_with_unknown_role,
        assignment_by_unknown_assigner,
    ],
)
def test_database_rejects(session: Session, violation):
    with pytest.raises(IntegrityError):
        violation(session)


def test_valid_rows_are_accepted_with_generated_ids(session: Session):
    unit_id = add_unit(session)
    role_id = add_role(session)
    admin_id = add_user(session, unit_id, "admin.one", "admin@demo.local")
    user_id = add_user(session, unit_id, "user.one", "one@demo.local")
    session.execute(
        insert(UserRole).values(user_id=user_id, role_id=role_id, assigned_by=admin_id)
    )
    user = session.get(AppUser, user_id)
    assert isinstance(user_id, uuid.UUID)
    assert user.status == "ACTIVE"
    assert user.created_at is not None
    assert user.role_codes == {"ROLE_A"}
