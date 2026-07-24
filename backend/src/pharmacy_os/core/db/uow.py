"""Unit of Work: one transaction boundary spanning repositories + events.

Use-cases open a UoW, do their work through repositories bound to the same
session, then :meth:`commit`. Domain events collected during the transaction
are published *after* a successful commit so subscribers never observe
uncommitted state.

**How events leave the transaction.** Without an :class:`OutboxSink` they are published
straight to the bus after the commit — simple, but there is a window in which the
business data is committed and the process dies before the dispatch, and the event is
then lost forever (the classic dual-write problem). With a sink, the events are
*written to the database inside the business transaction* and delivered from there, so
the change and its announcement succeed or fail together. Which sink — and whether it
also publishes immediately — is a composition decision; see ``core.outbox.sink``.
"""

from __future__ import annotations

from collections.abc import Sequence
from types import TracebackType
from typing import Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.events.base import DomainEvent
from pharmacy_os.core.events.bus import EventBus

StagedEvent = tuple[UUID, DomainEvent]
"""An event durably recorded, paired with the id of the row that now holds it."""


class OutboxSink(Protocol):
    """Where a Unit of Work hands its events for durable delivery.

    Declared here rather than imported from ``core.outbox`` on purpose: the UoW must
    not depend on the outbox implementation, and ``core.outbox`` already depends on
    this module's :class:`UnitOfWork`.
    """

    async def stage(
        self, session: AsyncSession, events: Sequence[DomainEvent]
    ) -> Sequence[StagedEvent]:
        """Record *events* on the caller's session, still inside its transaction."""
        ...

    async def after_commit(self, staged: Sequence[StagedEvent]) -> None:
        """Called once the business transaction is durable; may publish immediately."""
        ...


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
        outbox: OutboxSink | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._outbox = outbox
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
        events, self._events = self._events, []
        if self._outbox is None:
            await self.session.commit()
            for event in events:
                await self._event_bus.publish(event)
            return
        # Staged before the commit, so the outbox rows belong to the very transaction
        # that makes the business change durable: either both land or neither does.
        staged = await self._outbox.stage(self.session, events)
        await self.session.commit()
        await self._outbox.after_commit(staged)

    async def rollback(self) -> None:
        await self.session.rollback()
        self._events = []


class UnitOfWorkFactory:
    """Builds Units of Work already bound to the app's session factory, bus and outbox.

    One composed object, registered once in the container, so no module's ``register()``
    has to know how a UoW is assembled — in particular none of them has to remember to
    pass the outbox sink. A UoW built without one silently drops events on a crash, and
    that is not a mistake worth leaving a dozen chances to make.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: EventBus,
        outbox: OutboxSink | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._outbox = outbox

    def __call__(self) -> UnitOfWork:
        return SqlAlchemyUnitOfWork(self._session_factory, self._event_bus, self._outbox)
