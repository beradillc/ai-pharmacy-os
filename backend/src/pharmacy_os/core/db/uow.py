"""Unit of Work: one transaction boundary spanning repositories + events.

Use-cases open a UoW, do their work through repositories bound to the same
session, then :meth:`commit`. Domain events collected during the transaction
are published *after* a successful commit so subscribers never observe
uncommitted state.
"""

from __future__ import annotations

from types import TracebackType
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.events.base import DomainEvent
from pharmacy_os.core.events.bus import EventBus


class UnitOfWork(Protocol):
    session: AsyncSession

    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    def collect(self, event: DomainEvent) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: EventBus,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._events: list[DomainEvent] = []

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self.session = self._session_factory()
        self._events = []
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.session.close()

    def collect(self, event: DomainEvent) -> None:
        self._events.append(event)

    async def commit(self) -> None:
        await self.session.commit()
        events, self._events = self._events, []
        for event in events:
            await self._event_bus.publish(event)

    async def rollback(self) -> None:
        await self.session.rollback()
        self._events = []
