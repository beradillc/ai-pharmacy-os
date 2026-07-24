"""The flip: a Unit of Work now records its events in ``event_outbox`` when it commits.

This is the property the whole outbox exists for — the business write and the record of
the event it produced land in **one** transaction, so a crash can no longer commit a
sale whose ``SaleCompleted`` never reaches anybody. What happens after that commit is a
deployment choice (``OUTBOX__SYNC_DRAIN``), and both shapes are exercised here.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.events import DomainEvent, EventRegistry, InMemoryEventBus
from pharmacy_os.core.outbox import (
    OutboxEventSink,
    OutboxRelay,
    OutboxStatus,
    SqlAlchemyOutboxRepository,
)
from pharmacy_os.core.outbox.models import OutboxEventORM
from pharmacy_os.modules.sales.domain import SaleCompleted, SoldItem

SessionFactory = async_sessionmaker[AsyncSession]


def _sale(tenant_id: UUID) -> SaleCompleted:
    return SaleCompleted(
        tenant_id=tenant_id,
        order_id=uuid4(),
        branch_id=uuid4(),
        client_uuid=str(uuid4()),
        items=(SoldItem(drug_id=uuid4(), quantity=Decimal("2")),),
    )


async def _rows(session_factory: SessionFactory) -> list[OutboxEventORM]:
    async with session_factory() as session:
        result = await session.execute(select(OutboxEventORM))
        return list(result.scalars().all())


@pytest.fixture
def recorder() -> tuple[InMemoryEventBus, list[DomainEvent]]:
    bus = InMemoryEventBus()
    seen: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        seen.append(event)

    bus.subscribe(SaleCompleted, handler)
    return bus, seen


async def test_commit_writes_the_event_to_the_outbox_and_publishes_it(
    session_factory: SessionFactory,
    recorder: tuple[InMemoryEventBus, list[DomainEvent]],
    ctx: RequestContext,
) -> None:
    bus, seen = recorder
    sink = OutboxEventSink(session_factory, bus, sync_drain=True)
    event = _sale(ctx.tenant_id)

    async with SqlAlchemyUnitOfWork(session_factory, bus, sink) as uow:
        uow.collect(event)
        await uow.commit()

    # Subscribers still ran in-line, exactly as before the outbox existed...
    assert seen == [event]
    # ...but the event is now also on disk, and stamped as delivered.
    (row,) = await _rows(session_factory)
    assert row.event_id == event.event_id
    assert row.event_type == "SaleCompleted"
    assert row.tenant_id == ctx.tenant_id
    assert row.status == OutboxStatus.PUBLISHED.value
    assert row.published_at is not None


async def test_async_mode_leaves_the_event_pending_for_the_relay(
    session_factory: SessionFactory,
    recorder: tuple[InMemoryEventBus, list[DomainEvent]],
    ctx: RequestContext,
) -> None:
    bus, seen = recorder
    sink = OutboxEventSink(session_factory, bus, sync_drain=False)
    event = _sale(ctx.tenant_id)

    async with SqlAlchemyUnitOfWork(session_factory, bus, sink) as uow:
        uow.collect(event)
        await uow.commit()

    # Nothing was published in the request; the row is the promise that it will be.
    assert seen == []
    (row,) = await _rows(session_factory)
    assert row.status == OutboxStatus.PENDING.value

    registry = EventRegistry()
    registry.register(SaleCompleted)
    relay = OutboxRelay(
        lambda: SqlAlchemyUnitOfWork(session_factory, bus),
        lambda uow: SqlAlchemyOutboxRepository(uow.session),
        bus,
        registry,
    )
    result = await relay.drain_once()

    assert result.published == 1
    # Rebuilt from the stored payload — same event, not the in-memory instance.
    assert [e.event_id for e in seen] == [event.event_id]
    assert seen[0] == event
    (row,) = await _rows(session_factory)
    assert row.status == OutboxStatus.PUBLISHED.value


async def test_a_rolled_back_transaction_leaves_no_outbox_row(
    session_factory: SessionFactory,
    recorder: tuple[InMemoryEventBus, list[DomainEvent]],
    ctx: RequestContext,
) -> None:
    """Atomicity in the direction that matters: no business change, no announcement."""
    bus, seen = recorder
    sink = OutboxEventSink(session_factory, bus, sync_drain=True)

    with pytest.raises(RuntimeError):
        async with SqlAlchemyUnitOfWork(session_factory, bus, sink) as uow:
            uow.collect(_sale(ctx.tenant_id))
            raise RuntimeError("use-case failed before commit")

    assert await _rows(session_factory) == []
    assert seen == []


async def test_committing_nothing_writes_nothing(
    session_factory: SessionFactory,
    recorder: tuple[InMemoryEventBus, list[DomainEvent]],
) -> None:
    bus, seen = recorder
    sink = OutboxEventSink(session_factory, bus, sync_drain=True)

    async with SqlAlchemyUnitOfWork(session_factory, bus, sink) as uow:
        await uow.commit()

    assert await _rows(session_factory) == []
    assert seen == []


async def test_redelivery_is_possible_because_the_row_survives_a_lost_publish(
    session_factory: SessionFactory,
    recorder: tuple[InMemoryEventBus, list[DomainEvent]],
    ctx: RequestContext,
) -> None:
    """Simulates the crash the outbox exists for: committed, staged, never published.

    The row is left ``PENDING`` (as it would be after a hard kill between the commit
    and the dispatch) and the relay delivers it on the next pass — at-least-once, which
    is why subscribers must be idempotent.
    """
    bus, seen = recorder
    staging_only = OutboxEventSink(session_factory, bus, sync_drain=False)
    event = _sale(ctx.tenant_id)

    async with SqlAlchemyUnitOfWork(session_factory, bus, staging_only) as uow:
        uow.collect(event)
        await uow.commit()
    assert seen == []

    registry = EventRegistry()
    registry.register(SaleCompleted)

    def _uow() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, bus)

    relay = OutboxRelay(_uow, lambda uow: SqlAlchemyOutboxRepository(uow.session), bus, registry)
    assert (await relay.drain_once()).published == 1
    # A second pass finds nothing: the row is PUBLISHED, so recovery is not a re-send.
    assert (await relay.drain_once()).processed == 0
    assert len(seen) == 1
