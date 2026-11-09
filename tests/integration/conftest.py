"""Integration fixtures against the Compose Postgres (localhost:5433 via .env).

Every test database is created here with a random name and dropped afterwards;
the dev database named by POSTGRES_DB is never touched.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import URL, Connection, Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.main import create_app

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"
MAINTENANCE_DB = "postgres"


@contextmanager
def temporary_database() -> Iterator[URL]:
    settings = get_settings()
    name = f"lakehouse_test_{uuid4().hex[:12]}"
    admin = create_engine(settings.database_url(MAINTENANCE_DB), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
        yield settings.database_url(name)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def migrate(connection: Connection, revision: str, *, downgrade: bool = False) -> None:
    config = Config(str(ALEMBIC_INI))
    config.attributes["connection"] = connection
    (command.downgrade if downgrade else command.upgrade)(config, revision)


@pytest.fixture
def empty_database() -> Iterator[Engine]:
    with temporary_database() as url:
        engine = create_engine(url)
        yield engine
        engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """A test database migrated to head, shared by the session."""
    with temporary_database() as url:
        engine = create_engine(url)
        with engine.begin() as conn:
            migrate(conn, "head")
        yield engine
        engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    """A session whose work (including commits) is rolled back after the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    """API client whose requests share the test's rolled-back session."""
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
