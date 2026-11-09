"""Identity tables: organization units, users, roles and role assignments (docs/erd.mmd)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, Status


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(primary_key=True, server_default=func.gen_random_uuid())


def status_column() -> Mapped[str]:
    return mapped_column(String(20), server_default=Status.ACTIVE.value)


def created_now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class OrganizationUnit(Base):
    __tablename__ = "organization_unit"

    unit_id: Mapped[uuid.UUID] = uuid_pk()
    unit_code: Mapped[str] = mapped_column(String(50), unique=True)
    unit_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = status_column()


class Role(Base):
    __tablename__ = "role"

    role_id: Mapped[uuid.UUID] = uuid_pk()
    role_code: Mapped[str] = mapped_column(String(50), unique=True)
    role_name: Mapped[str] = mapped_column(String(200))


class AppUser(Base):
    __tablename__ = "app_user"

    user_id: Mapped[uuid.UUID] = uuid_pk()
    unit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organization_unit.unit_id"))
    username: Mapped[str] = mapped_column(String(100), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = status_column()
    created_at: Mapped[datetime] = created_now()

    unit: Mapped[OrganizationUnit] = relationship()
    # Read side of USER_ROLE; assignments are written through UserRole.
    roles: Mapped[list[Role]] = relationship(
        secondary="user_role",
        primaryjoin="AppUser.user_id == UserRole.user_id",
        secondaryjoin="Role.role_id == UserRole.role_id",
        order_by="Role.role_code",
        viewonly=True,
    )

    @property
    def role_codes(self) -> frozenset[str]:
        return frozenset(role.role_code for role in self.roles)


class UserRole(Base):
    __tablename__ = "user_role"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.user_id"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("role.role_id"), primary_key=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.user_id"))
    assigned_at: Mapped[datetime] = created_now()
