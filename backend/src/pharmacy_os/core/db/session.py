"""Async engine and session factory construction."""

from __future__ import annotations

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(url: str, *, pool_size: int = 10, echo: bool = False) -> AsyncEngine:
    """Create the async SQLAlchemy engine.

    SQLite (used in tests) does not accept pool sizing, so we only pass it for
    server-backed databases. SQLite also doesn't enforce foreign keys unless told
    to per-connection — enabled here so its behavior matches Postgres (which
    always enforces FKs), otherwise cross-module FK constraints like
    ``customer_allergies.ingredient_id`` would silently no-op under SQLite tests.
    """
    kwargs: dict[str, object] = {"echo": echo, "future": True}
    if not url.startswith("sqlite"):
        kwargs["pool_size"] = pool_size
        kwargs["pool_pre_ping"] = True
    engine = create_async_engine(url, **kwargs)
    if url.startswith("sqlite"):
        _enable_sqlite_foreign_keys(engine)
    return engine


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
