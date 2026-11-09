"""Seed synthetic demo identities. Idempotent: re-running converges to the same rows.

Run inside Compose:  docker compose exec api python -m scripts.seed_demo_data
All names and emails are fictitious.
"""

import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.security import RoleCode
from app.db.models import AppUser, OrganizationUnit, Role, Status, UserRole
from app.db.session import get_session_factory

logger = logging.getLogger("scripts.seed_demo_data")

UNITS: dict[str, str] = {
    "RETAIL": "Retail Banking",
    "LENDING": "Lending",
    "FINANCE": "Finance",
    "HUMAN_CAPITAL": "Human Capital",
}

ROLES: dict[RoleCode, str] = {
    RoleCode.DATA_SUBMITTER: "Data Submitter",
    RoleCode.DATA_STEWARD: "Data Steward",
    RoleCode.PLATFORM_ADMIN: "Platform Admin",
    RoleCode.SECURITY_REVIEWER: "Security Reviewer",
    RoleCode.DATA_CONSUMER: "Central Data Consumer",
}


@dataclass(frozen=True)
class DemoUser:
    username: str
    display_name: str
    unit_code: str
    roles: tuple[RoleCode, ...]

    @property
    def email(self) -> str:
        return f"{self.username}@demo.local"


DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser("sari.submitter", "Sari Wulandari", "RETAIL", (RoleCode.DATA_SUBMITTER,)),
    DemoUser("dimas.steward", "Dimas Pratama", "LENDING", (RoleCode.DATA_STEWARD,)),
    DemoUser("andi.admin", "Andi Nugroho", "FINANCE", (RoleCode.PLATFORM_ADMIN,)),
    DemoUser("maya.security", "Maya Kusuma", "HUMAN_CAPITAL", (RoleCode.SECURITY_REVIEWER,)),
    DemoUser("rizky.consumer", "Rizky Saputra", "FINANCE", (RoleCode.DATA_CONSUMER,)),
)


def seed(session: Session) -> dict[str, int]:
    """Upsert units, roles, users and role assignments by natural key; commit; return counts."""
    stmt = insert(OrganizationUnit).values(
        [{"unit_code": c, "unit_name": n, "status": Status.ACTIVE} for c, n in UNITS.items()]
    )
    unit_ids = dict(
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[OrganizationUnit.unit_code],
                set_={"unit_name": stmt.excluded.unit_name, "status": stmt.excluded.status},
            ).returning(OrganizationUnit.unit_code, OrganizationUnit.unit_id)
        ).all()
    )

    stmt = insert(Role).values([{"role_code": c, "role_name": n} for c, n in ROLES.items()])
    role_ids = dict(
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[Role.role_code], set_={"role_name": stmt.excluded.role_name}
            ).returning(Role.role_code, Role.role_id)
        ).all()
    )

    stmt = insert(AppUser).values(
        [
            {
                "username": u.username,
                "email": u.email,
                "display_name": u.display_name,
                "unit_id": unit_ids[u.unit_code],
                "status": Status.ACTIVE,
            }
            for u in DEMO_USERS
        ]
    )
    user_ids = dict(
        session.execute(
            stmt.on_conflict_do_update(
                index_elements=[AppUser.username],
                set_={
                    col: stmt.excluded[col] for col in ("email", "display_name", "unit_id", "status")
                },
            ).returning(AppUser.username, AppUser.user_id)
        ).all()
    )

    session.execute(
        insert(UserRole)
        .values(
            [
                {"user_id": user_ids[u.username], "role_id": role_ids[role]}
                for u in DEMO_USERS
                for role in u.roles
            ]
        )
        .on_conflict_do_nothing(index_elements=[UserRole.user_id, UserRole.role_id])
    )
    session.commit()
    return row_counts(session)


def row_counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: session.scalar(select(func.count()).select_from(model))
        for model in (OrganizationUnit, Role, AppUser, UserRole)
    }


def main() -> None:
    configure_logging(get_settings().log_level)
    with get_session_factory()() as session:
        counts = seed(session)
    logger.info("demo data seeded", extra={"row_counts": counts})


if __name__ == "__main__":
    main()
