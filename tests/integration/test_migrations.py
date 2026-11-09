"""The baseline migration: reversible, matches docs/erd.mmd, and matches the ORM models."""

import re
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import Engine, inspect

from app.db.models import Base
from tests.integration.conftest import migrate

ERD = Path(__file__).resolve().parents[2] / "docs" / "erd.mmd"
IDENTITY_TABLES = ("organization_unit", "app_user", "role", "user_role")
# ERD type -> reflected PostgreSQL type name
ERD_TYPES = {"uuid": "UUID", "varchar": "VARCHAR", "timestamp": "TIMESTAMP"}


def erd_entity(table: str) -> list[tuple[str, str, set[str]]]:
    """[(column, erd_type, {"PK", "FK", "UK"}), ...] for one ERD entity, in ERD order."""
    match = re.search(rf"^\s*{table.upper()} \{{\n(.*?)^\s*\}}", ERD.read_text(), re.M | re.S)
    assert match, f"{table} not found in {ERD}"
    columns = []
    for line in match.group(1).strip().splitlines():
        erd_type, name, *keys = line.split(maxsplit=2)
        columns.append((name, erd_type, {k.strip() for k in "".join(keys).split(",") if k}))
    return columns


def user_tables(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names()) - {"alembic_version"}


def test_upgrade_downgrade_upgrade(empty_database: Engine):
    with empty_database.begin() as conn:
        migrate(conn, "head")
    assert user_tables(empty_database) == set(IDENTITY_TABLES)

    with empty_database.begin() as conn:
        migrate(conn, "base", downgrade=True)
    assert user_tables(empty_database) == set()

    with empty_database.begin() as conn:
        migrate(conn, "head")
    assert user_tables(empty_database) == set(IDENTITY_TABLES)


def test_tables_match_the_erd(engine: Engine):
    inspector = inspect(engine)
    for table in IDENTITY_TABLES:
        expected = erd_entity(table)
        reflected = inspector.get_columns(table)

        assert [c["name"] for c in reflected] == [name for name, _, _ in expected], table
        for column, (name, erd_type, _) in zip(reflected, expected, strict=True):
            assert type(column["type"]).__name__ == ERD_TYPES[erd_type], f"{table}.{name}"

        def with_key(key: str) -> set[str]:
            return {name for name, _, keys in expected if key in keys}

        pk = set(inspector.get_pk_constraint(table)["constrained_columns"])
        fks = {c for fk in inspector.get_foreign_keys(table) for c in fk["constrained_columns"]}
        uniques = {
            c
            for uq in inspector.get_unique_constraints(table)
            for c in uq["column_names"]
        }
        assert pk == with_key("PK"), table
        assert fks == with_key("FK"), table
        assert uniques == with_key("UK"), table


def test_uuid_primary_keys_default_to_gen_random_uuid(engine: Engine):
    inspector = inspect(engine)
    for table in ("organization_unit", "app_user", "role"):
        (pk,) = inspector.get_pk_constraint(table)["constrained_columns"]
        column = next(c for c in inspector.get_columns(table) if c["name"] == pk)
        assert column["default"] == "gen_random_uuid()", table


def test_models_match_the_migrated_schema(engine: Engine):
    with engine.connect() as conn:
        assert compare_metadata(MigrationContext.configure(conn), Base.metadata) == []
