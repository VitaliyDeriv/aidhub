from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str, pool_size: int = 5, max_overflow: int = 10) -> Engine:
    if url.startswith("sqlite"):
        # SQLite використовується лише в автотестах (in-memory).
        options: dict = {"connect_args": {"check_same_thread": False}}
        if url == "sqlite://" or ":memory:" in url:
            options["poolclass"] = StaticPool
        return create_engine(url, **options)
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )


_settings = get_settings()
engine = make_engine(_settings.database_url, _settings.db_pool_size, _settings.db_max_overflow)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
