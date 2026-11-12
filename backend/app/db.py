import os
from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


class DatabaseConfigurationError(RuntimeError):
    pass


def database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url or not url.strip():
        raise DatabaseConfigurationError("DATABASE_URL is required")
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine())


def get_db() -> Iterator[Session]:
    create_session = session_factory()
    with create_session() as session:
        yield session
