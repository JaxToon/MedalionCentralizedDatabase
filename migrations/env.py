"""Alembic environment.

Uses the connection passed in `config.attributes["connection"]` when present
(tests), otherwise connects with the URL from app settings.
"""

from alembic import context
from sqlalchemy import Connection, create_engine

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.models import Base

config = context.config
target_metadata = Base.metadata

if "connection" not in config.attributes:  # CLI run; tests keep their own logging
    configure_logging(get_settings().log_level)


def run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        run_migrations(connection)
        return
    engine = create_engine(get_settings().database_url())
    try:
        with engine.connect() as connection:
            run_migrations(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise SystemExit("Offline (--sql) migrations are not supported; run against a database.")
run_migrations_online()
