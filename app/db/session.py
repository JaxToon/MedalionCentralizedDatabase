"""Engine and session factory, created lazily from settings on first use."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    engine: Engine = create_engine(
        get_settings().database_url(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5},
    )
    return sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with get_session_factory()() as session:
        yield session
