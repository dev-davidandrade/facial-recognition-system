from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from face_access.config.settings import Settings


class Database:
    def __init__(self, database_url: str) -> None:
        self.engine: Engine = create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )


@lru_cache
def get_database() -> Database:
    return Database(Settings().database_url)


def get_session() -> Iterator[Session]:
    session = get_database().session_factory()
    try:
        yield session
    finally:
        session.close()
