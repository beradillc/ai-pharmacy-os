"""Integration tests for the automatic DAV re-push loop — docs/13 mục D.4.

Covers the gap the manual re-POST used to fill: a rejected push leaves a queued task, a
background drain re-drives it, and the queue is bounded (backoff, lease, dead letter).
The clock is injected so a multi-hour backoff schedule is exercised in milliseconds.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.compliance.application import (
    NationalSyncRetryRelay,
    NationalSyncService,
    PushSyncInput,
    SyncRetryConfig,
)
from pharmacy_os.modules.compliance.domain import (
    NationalDrugDbGateway,
    SyncAck,
    SyncPayloadType,
    SyncRequest,
    SyncRetryStatus,
    SyncStatus,
)
from pharmacy_os.modules.compliance.infrastructure import (
    NationalSyncLogORM,
    NationalSyncRetryTaskORM,
    SqlAlchemyNationalSyncLogRepository,
    SqlAlchemyNationalSyncRetryClaimer,
    SqlAlchemyNationalSyncRetryQueue,
)

_START = datetime(2026, 7, 25, 9, 0, tzinfo=UTC)


class _FlakyGateway:
    """Rejects until :attr:`ok` is flipped — the "cổng bảo trì rồi sống lại" case."""

    def __init__(self) -> None:
        self.ok = False
        self.calls = 0

    async def push(self, request: SyncRequest) -> SyncAck:
        self.calls += 1
        if self.ok:
            return SyncAck(ok=True, response_code="200", response_body='{"ack":true}')
        return SyncAck(ok=False, response_code="503", response_body="unavailable")


class _MovableClock:
    """A clock the test winds forward, so backoff windows cost no wall-clock time."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += timedelta(seconds=seconds)


def _ctx() -> RequestContext:
    return RequestContext(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
        permissions=frozenset({"compliance.sync.push", "compliance.sync.read"}),
    )


@pytest.fixture
def sync_ctx() -> RequestContext:
    return _ctx()


Wired = tuple[NationalSyncService, NationalSyncRetryRelay]
Builder = Callable[[NationalDrugDbGateway, _MovableClock, SyncRetryConfig], Wired]


@pytest.fixture
def build(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> Builder:
    def _build(
        gateway: NationalDrugDbGateway, clock: _MovableClock, config: SyncRetryConfig
    ) -> Wired:
        def uow_factory() -> UnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory, event_bus)

        def log_repo(uow: UnitOfWork, c: RequestContext) -> SqlAlchemyNationalSyncLogRepository:
            return SqlAlchemyNationalSyncLogRepository(uow.session, c)

        def queue(uow: UnitOfWork, c: RequestContext) -> SqlAlchemyNationalSyncRetryQueue:
            return SqlAlchemyNationalSyncRetryQueue(uow.session, c)

        def claimer(uow: UnitOfWork) -> SqlAlchemyNationalSyncRetryClaimer:
            return SqlAlchemyNationalSyncRetryClaimer(uow.session)

        service = NationalSyncService(uow_factory, log_repo, gateway, queue)
        relay = NationalSyncRetryRelay(uow_factory, claimer, service, config, clock)
        return service, relay

    return _build


def _payload(**kw: object) -> PushSyncInput:
    kw.setdefault("payload_type", SyncPayloadType.SALE)
    kw.setdefault("client_uuid", "cli-retry-001")
    kw.setdefault("payload", '{"order_id":"7","items":[]}')
    return PushSyncInput(**kw)  # type: ignore[arg-type]


async def _tasks(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[NationalSyncRetryTaskORM]:
    async with session_factory() as session:
        rows = await session.execute(select(NationalSyncRetryTaskORM))
        return list(rows.scalars().all())


async def _log_count(session_factory: async_sessionmaker[AsyncSession]) -> int:
    async with session_factory() as session:
        return int((await session.execute(select(func.count(NationalSyncLogORM.id)))).scalar_one())


async def test_a_rejected_push_queues_the_payload_for_retry(
    build: Builder, sync_ctx: RequestContext, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service, _ = build(_FlakyGateway(), _MovableClock(_START), SyncRetryConfig())

    out = await service.push_payload(_payload(), sync_ctx)

    assert out.status == SyncStatus.FAILED.value
    (task,) = await _tasks(session_factory)
    assert task.client_uuid == "cli-retry-001"
    assert task.payload == '{"order_id":"7","items":[]}'  # kept only because it never landed
    assert task.sync_log_id == out.id
    assert task.status == SyncRetryStatus.PENDING.value
    assert task.attempt_count == 0


async def test_an_acked_push_queues_nothing(
    build: Builder, sync_ctx: RequestContext, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    gateway = _FlakyGateway()
    gateway.ok = True
    service, _ = build(gateway, _MovableClock(_START), SyncRetryConfig())

    out = await service.push_payload(_payload(), sync_ctx)

    assert out.status == SyncStatus.ACK.value
    assert await _tasks(session_factory) == []


async def test_pushing_the_same_record_twice_queues_one_task_not_two(
    build: Builder, sync_ctx: RequestContext, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    service, _ = build(_FlakyGateway(), _MovableClock(_START), SyncRetryConfig())

    await service.push_payload(_payload(), sync_ctx)
    await service.push_payload(_payload(), sync_ctx)

    assert len(await _tasks(session_factory)) == 1


async def test_the_relay_repushes_and_purges_the_payload_once_it_lands(
    build: Builder, sync_ctx: RequestContext, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    gateway = _FlakyGateway()
    clock = _MovableClock(_START)
    service, relay = build(gateway, clock, SyncRetryConfig(base_backoff_seconds=60.0))
    out = await service.push_payload(_payload(), sync_ctx)

    first = await relay.drain_once()  # gateway still down
    assert (first.retried, first.acked) == (1, 0)
    (task,) = await _tasks(session_factory)
    assert task.attempt_count == 1

    gateway.ok = True
    clock.advance(60)
    second = await relay.drain_once()

    assert (second.acked, second.retried, second.dead) == (1, 0, 0)
    assert await _tasks(session_factory) == []  # payload gone the moment the duty is discharged
    assert (await service.get_sync_log(out.id, sync_ctx)).status == SyncStatus.ACK.value
    assert await _log_count(session_factory) == 1  # same audit row reused, not a second one


async def test_a_task_is_not_retried_before_its_backoff_elapses(
    build: Builder, sync_ctx: RequestContext
) -> None:
    clock = _MovableClock(_START)
    service, relay = build(_FlakyGateway(), clock, SyncRetryConfig(base_backoff_seconds=60.0))
    await service.push_payload(_payload(), sync_ctx)
    await relay.drain_once()

    assert (await relay.drain_once()).processed == 0  # still inside the 60s window
    clock.advance(59)
    assert (await relay.drain_once()).processed == 0
    clock.advance(1)
    assert (await relay.drain_once()).processed == 1


async def test_retries_are_bounded_and_the_task_dead_letters(
    build: Builder, sync_ctx: RequestContext, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    gateway = _FlakyGateway()
    clock = _MovableClock(_START)
    service, relay = build(gateway, clock, SyncRetryConfig(max_retries=3, base_backoff_seconds=1.0))
    await service.push_payload(_payload(), sync_ctx)

    for delay in (0.0, 1.0, 2.0):
        clock.advance(delay)
        await relay.drain_once()

    (task,) = await _tasks(session_factory)
    assert task.status == SyncRetryStatus.DEAD.value
    assert task.attempt_count == 3
    assert task.payload  # dead letters keep the payload — the record still has to get there

    calls_so_far = gateway.calls
    clock.advance(365 * 24 * 3600)
    assert (await relay.drain_once()).processed == 0  # never hammered again
    assert gateway.calls == calls_so_far


async def test_a_claimed_task_is_leased_away_from_a_second_drain(
    build: Builder, sync_ctx: RequestContext, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """Two relays (or two app instances) must not both push the same record."""
    clock = _MovableClock(_START)
    service, _ = build(_FlakyGateway(), clock, SyncRetryConfig())
    await service.push_payload(_payload(), sync_ctx)

    lease_until = _START + timedelta(seconds=300)
    async with session_factory() as session:
        first = await SqlAlchemyNationalSyncRetryClaimer(session).claim_due(
            _START, limit=10, lease_until=lease_until
        )
        await session.commit()
    async with session_factory() as session:
        second = await SqlAlchemyNationalSyncRetryClaimer(session).claim_due(
            _START, limit=10, lease_until=lease_until
        )
        third = await SqlAlchemyNationalSyncRetryClaimer(session).claim_due(
            lease_until, limit=10, lease_until=lease_until + timedelta(seconds=300)
        )

    assert len(first) == 1
    assert second == []  # hidden while the lease holds
    assert len(third) == 1  # a crashed relay loses the lease, not the work


async def test_one_drain_covers_every_tenant(
    build: Builder, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """The relay runs outside any request, so it must not be tenant-scoped."""
    gateway = _FlakyGateway()
    clock = _MovableClock(_START)
    service, relay = build(gateway, clock, SyncRetryConfig())
    for tenant_no in range(3):
        await service.push_payload(_payload(client_uuid=f"cli-{tenant_no}"), _ctx())

    gateway.ok = True
    assert (await relay.drain_once()).acked == 3
    assert await _tasks(session_factory) == []
