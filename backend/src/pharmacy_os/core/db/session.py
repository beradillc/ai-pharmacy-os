"""Async engine and session factory construction."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(url: str, *, pool_size: int = 10, echo: bool = False) -> AsyncEngine:
    """Create the async SQLAlchemy engine.

    SQLite (used in tests) does not accept pool sizing, so we only pass it for
    server-backed databases.
    """
    kwargs: dict[str, object] = {"echo": echo, "future": True}
    if not url.startswith("sqlite"):
        kwargs["pool_size"] = pool_size
        kwargs["pool_pre_ping"] = True
    return create_async_engine(url, **kwargs)


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
