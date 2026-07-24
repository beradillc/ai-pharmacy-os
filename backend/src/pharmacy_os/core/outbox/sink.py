"""The Unit of Work's end of the outbox: record events, then (optionally) publish.

:meth:`OutboxEventSink.stage` writes one ``event_outbox`` row per collected event on
the *business* session, so the rows commit atomically with the data that produced them.
What happens next is the deployment's choice:

* ``sync_drain=True`` — :meth:`after_commit` publishes each event on the bus right away
  and stamps its row ``PUBLISHED``. Subscribers therefore run in the same request, in
  the same order as before the outbox existed (dev, tests, and any deployment that
  wants the old latency); the difference is that a crash between the commit and the
  publish now leaves a ``PENDING`` row for the relay instead of losing the event.
* ``sync_drain=False`` — :meth:`after_commit` does nothing and
  :class:`~pharmacy_os.core.outbox.relay.OutboxRelay` delivers out of band. Requests
  return without waiting for subscribers; the system becomes eventually consistent.

Either way delivery is **at-least-once**: an event may reach a subscriber twice (a
crash after publishing but before the row is stamped), which is why every subscriber
carries an idempotency key.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.db.uow import StagedEvent
from pharmacy_os.core.events import DomainEvent, EventBus, serialize_event
from pharmacy_os.core.outbox.record import OutboxRecord
from pharmacy_os.core.outbox.repository import SqlAlchemyOutboxRepository

Clock = Callable[[], datetime]


def _default_clock() -> datetime:
    return datetime.now(UTC)


class OutboxEventSink:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        event_bus: EventBus,
        *,
        sync_drain: bool = True,
        clock: Clock = _default_clock,
    ) -> None:
        self._session_factory = session_factory
        self._event_bus = event_bus
        self._sync_drain = sync_drain
        self._now = clock

    async def stage(
        self, session: AsyncSession, events: Sequence[DomainEvent]
    ) -> Sequence[StagedEvent]:
        if not events:
            return ()
        repo = SqlAlchemyOutboxRepository(session)
        staged: list[StagedEvent] = []
        for event in events:
            encoded = serialize_event(event)
            record = OutboxRecord.pending(
                event_id=event.event_id,
                event_type=encoded["event_type"],
                tenant_id=event.tenant_id,
                payload=encoded["payload"],
                occurred_at=event.occurred_at,
            )
            await repo.add(record)
            staged.append((record.id, event))
        return staged

    async def after_commit(self, staged: Sequence[StagedEvent]) -> None:
        if not self._sync_drain or not staged:
            return
        # Publish first, stamp second: the reverse order would mark an event delivered
        # that a crash then prevented from ever being delivered. The in-memory bus
        # isolates subscriber failures, so this cannot raise.
        for _record_id, event in staged:
            await self._event_bus.publish(event)
        now = self._now()
        # A separate transaction on purpose — the business one is already committed,
        # and a subscriber may have committed work of its own in between.
        async with self._session_factory() as session:
            repo = SqlAlchemyOutboxRepository(session)
            for record_id, _event in staged:
                await repo.mark_published(record_id, now)
            await session.commit()
