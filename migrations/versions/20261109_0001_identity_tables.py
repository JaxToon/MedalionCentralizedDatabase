"""Identity tables: organization_unit, app_user, role, user_role.

Revision ID: 0001
Revises:
Create Date: 2026-11-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def uuid_pk(name: str) -> sa.Column:
    return sa.Column(name, sa.Uuid(), server_default=sa.func.gen_random_uuid(), nullable=False)


def status() -> sa.Column:
    return sa.Column("status", sa.String(20), server_default="ACTIVE", nullable=False)


def created_now(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "organization_unit",
        uuid_pk("unit_id"),
        sa.Column("unit_code", sa.String(50), nullable=False),
        sa.Column("unit_name", sa.String(200), nullable=False),
        status(),
        sa.PrimaryKeyConstraint("unit_id", name="pk_organization_unit"),
        sa.UniqueConstraint("unit_code", name="uq_organization_unit_unit_code"),
    )
    op.create_table(
        "app_user",
        uuid_pk("user_id"),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        status(),
        created_now("created_at"),
        sa.PrimaryKeyConstraint("user_id", name="pk_app_user"),
        sa.ForeignKeyConstraint(
            ["unit_id"],
            ["organization_unit.unit_id"],
            name="fk_app_user_unit_id_organization_unit",
        ),
        sa.UniqueConstraint("username", name="uq_app_user_username"),
        sa.UniqueConstraint("email", name="uq_app_user_email"),
    )
    op.create_table(
        "role",
        uuid_pk("role_id"),
        sa.Column("role_code", sa.String(50), nullable=False),
        sa.Column("role_name", sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint("role_id", name="pk_role"),
        sa.UniqueConstraint("role_code", name="uq_role_role_code"),
    )
    op.create_table(
        "user_role",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        created_now("assigned_at"),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_role"),
        sa.ForeignKeyConstraint(
            ["user_id"], ["app_user.user_id"], name="fk_user_role_user_id_app_user"
        ),
        sa.ForeignKeyConstraint(["role_id"], ["role.role_id"], name="fk_user_role_role_id_role"),
        sa.ForeignKeyConstraint(
            ["assigned_by"], ["app_user.user_id"], name="fk_user_role_assigned_by_app_user"
        ),
    )


def downgrade() -> None:
    op.drop_table("user_role")
    op.drop_table("role")
    op.drop_table("app_user")
    op.drop_table("organization_unit")
