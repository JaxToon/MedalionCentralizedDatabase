"""The demo seed covers every role and is idempotent."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import RoleCode
from app.db.models import AppUser, OrganizationUnit, Role, UserRole
from scripts.seed_demo_data import seed


def snapshot(session: Session) -> dict[str, list[tuple]]:
    """Every identity row, ids included, in a stable order."""
    return {
        "units": session.execute(select(OrganizationUnit.__table__).order_by("unit_code")).all(),
        "roles": session.execute(select(Role.__table__).order_by("role_code")).all(),
        "users": session.execute(select(AppUser.__table__).order_by("username")).all(),
        "user_roles": session.execute(
            select(UserRole.__table__).order_by("user_id", "role_id")
        ).all(),
    }


def test_seed_creates_units_roles_and_a_user_per_role(session: Session):
    counts = seed(session)

    assert counts["organization_unit"] == 4
    assert counts["role"] == 5
    assert set(session.scalars(select(OrganizationUnit.unit_name))) == {
        "Retail Banking",
        "Lending",
        "Finance",
        "Human Capital",
    }
    users = session.scalars(select(AppUser)).all()
    assert all(user.email.endswith("@demo.local") for user in users)
    assert set().union(*(user.role_codes for user in users)) == set(RoleCode)


def test_seed_is_idempotent(session: Session):
    first_counts = seed(session)
    first = snapshot(session)

    second_counts = seed(session)
    second = snapshot(session)

    assert second_counts == first_counts
    assert second == first
