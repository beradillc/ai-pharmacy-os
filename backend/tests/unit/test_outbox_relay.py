"""Relay logic in isolation: a fake repository, a real bus and registry.

No database here — these pin the drain/retry/dead-letter decisions. Repository
persistence is covered separately in ``tests/integration/test_outbox_repository.py``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from pharmacy_os.core.events import (
    DomainEvent,
    EventRegistry,
    InMemoryEventBus,
    serialize_event,
)
from pharmacy_os.core.outbox import (
    OutboxRecord,
    OutboxRelay,
    OutboxRelayConfig,
    OutboxStatus,
)


@dataclass(frozen=True, kw_only=True)
class _Sample(DomainEvent):
    note: str = "hi"


class _FakeUow:
    """Just enough of the UnitOfWork protocol for the relay: a marker + commit count."""

    def __init__(self) -> None:
        self.session = self  # relay passes `uow` to repo_factory; the fake repo ignores it
        self.commits = 0

    async def __aenter__(self) -> _FakeUow:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1


@dataclass
class _FakeRepo:
    """In-memory outbox: enough to observe claim/mark transitions."""

    rows: dict[UUID, OutboxRecord] = field(default_factory=dict)

    def seed(self, record: OutboxRecord) -> None:
        self.rows[record.id] = record

    async def add(self, record: OutboxRecord) -> None:
        self.rows[record.id] = record

    async def claim_pending(self, now: datetime, *, limit: int) -> list[OutboxRecord]:
        due = [
            r
            for r in self.rows.values()
            if r.status is OutboxStatus.PENDING
            and (r.next_attempt_at is None or r.next_attempt_at <= now)
        ]
        due.sort(key=lambda r: (r.occurred_at, r.id))
        return due[:limit]

    async def mark_published(self, record_id: UUID, published_at: datetime) -> None:
        self.rows[record_id] = replace(
            self.rows[record_id],
            status=OutboxStatus.PUBLISHED,
            published_at=published_at,
        )

    async def mark_retry(
        self, record_id: UUID, *, retry_count: int, next_attempt_at: datetime, last_error: str
    ) -> None:
        self.rows[record_id] = replace(
            self.rows[record_id],
            status=OutboxStatus.PENDING,
            retry_count=retry_count,
            next_attempt_at=next_attempt_at,
            last_error=last_error,
        )

    async def mark_failed(self, record_id: UUID, *, retry_count: int, last_error: str) -> None:
        self.rows[record_id] = replace(
            self.rows[record_id],
            status=OutboxStatus.FAILED,
            retry_count=retry_count,
            last_error=last_error,
        )


def _record_for(event: DomainEvent) -> OutboxRecord:
    data = serialize_event(event)
    return OutboxRecord.pending(
        event_id=event.event_id,
        event_type=data["event_type"],
        tenant_id=event.tenant_id,
        payload=data["payload"],
        occurred_at=event.occurred_at,
    )


def _relay(
    repo: _FakeRepo,
    *,
    registry: EventRegistry,
    bus: InMemoryEventBus,
    now: datetime,
    config: OutboxRelayConfig | None = None,
) -> tuple[OutboxRelay, _FakeUow]:
    uow = _FakeUow()
    relay = OutboxRelay(
        uow_factory=lambda: uow,  # type: ignore[arg-type,return-value]
        repo_factory=lambda _uow: repo,  # type: ignore[arg-type,return-value]
        event_bus=bus,
        registry=registry,
        config=config,
        clock=lambda: now,
    )
    return relay, uow


async def test_drain_publishes_and_delivers_to_subscriber() -> None:
    event = _Sample(tenant_id=uuid4(), note="dispense me")
    registry = EventRegistry()
    registry.register(_Sample)
    bus = InMemoryEventBus()
    seen: list[DomainEvent] = []

    async def _record_seen(e: DomainEvent) -> None:
        seen.append(e)

    bus.subscribe(_Sample, _record_seen)

    repo = _FakeRepo()
    repo.seed(_record_for(event))
    now = datetime.now(UTC)
    relay, uow = _relay(repo, registry=registry, bus=bus, now=now)

    result = await relay.drain_once()

    assert result.published == 1 and result.processed == 1
    assert uow.commits == 1
    # The real event object reached the subscriber, reconstructed via the codec.
    assert len(seen) == 1
    assert isinstance(seen[0], _Sample) and seen[0].note == "dispense me"
    assert seen[0].event_id == event.event_id
    stored = next(iter(repo.rows.values()))
    assert stored.status is OutboxStatus.PUBLISHED and stored.published_at == now


async def test_unknown_event_type_retries_then_dead_letters() -> None:
    # Registry left empty -> resolve() returns None -> delivery error every attempt.
    event = _Sample(tenant_id=uuid4())
    registry = EventRegistry()
    bus = InMemoryEventBus()
    repo = _FakeRepo()
    repo.seed(_record_for(event))
    config = OutboxRelayConfig(max_retries=3, base_backoff_seconds=1.0)

    row_id = next(iter(repo.rows))
    now = datetime.now(UTC)

    # Attempt 1 -> retry_count 1, scheduled +1s.
    relay, _ = _relay(repo, registry=registry, bus=bus, now=now, config=config)
    r1 = await relay.drain_once()
    assert r1.retried == 1 and r1.failed == 0
    row = repo.rows[row_id]
    assert row.status is OutboxStatus.PENDING and row.retry_count == 1
    assert row.next_attempt_at == now + timedelta(seconds=1.0)
    assert row.last_error is not None and "unknown event_type" in row.last_error

    # Not yet due -> claim skips it.
    relay_early, _ = _relay(repo, registry=registry, bus=bus, now=now, config=config)
    assert (await relay_early.drain_once()).processed == 0

    # Attempt 2 (due) -> retry_count 2, backoff doubles to +2s.
    t2 = now + timedelta(seconds=1.0)
    relay2, _ = _relay(repo, registry=registry, bus=bus, now=t2, config=config)
    await relay2.drain_once()
    assert repo.rows[row_id].retry_count == 2
    assert repo.rows[row_id].next_attempt_at == t2 + timedelta(seconds=2.0)

    # Attempt 3 reaches max_retries -> dead-letter.
    t3 = t2 + timedelta(seconds=2.0)
    relay3, _ = _relay(repo, registry=registry, bus=bus, now=t3, config=config)
    r3 = await relay3.drain_once()
    assert r3.failed == 1
    assert repo.rows[row_id].status is OutboxStatus.FAILED
    assert repo.rows[row_id].retry_count == 3


async def test_publish_error_is_retried() -> None:
    event = _Sample(tenant_id=uuid4())
    registry = EventRegistry()
    registry.register(_Sample)

    class _BoomBus:
        def subscribe(self, *a: object, **k: object) -> None: ...
        async def publish(self, event: DomainEvent) -> None:
            raise RuntimeError("bus down")

    repo = _FakeRepo()
    repo.seed(_record_for(event))
    row_id = next(iter(repo.rows))
    now = datetime.now(UTC)
    relay, _ = _relay(
        repo,
        registry=registry,
        bus=_BoomBus(),  # type: ignore[arg-type]
        now=now,
        config=OutboxRelayConfig(max_retries=5, base_backoff_seconds=2.0),
    )

    result = await relay.drain_once()

    assert result.retried == 1
    row = repo.rows[row_id]
    assert row.status is OutboxStatus.PENDING and row.retry_count == 1
    assert row.last_error is not None and "bus down" in row.last_error


async def test_empty_drain_is_a_noop() -> None:
    relay, uow = _relay(
        _FakeRepo(), registry=EventRegistry(), bus=InMemoryEventBus(), now=datetime.now(UTC)
    )
    result = await relay.drain_once()
    assert result.processed == 0
    assert uow.commits == 1


@pytest.mark.parametrize("attempt,expected", [(1, 2.0), (2, 4.0), (3, 8.0)])
def test_backoff_doubles(attempt: int, expected: float) -> None:
    # Documents the schedule the retry test relies on: base * 2**(attempt-1).
    base = 2.0
    assert base * 2 ** (attempt - 1) == expected


async def test_run_forever_keeps_draining_until_cancelled() -> None:
    """The background loop: work arriving later is still picked up, and a failed
    drain doesn't kill the loop — the rows are still there for the next tick."""
    registry = EventRegistry()
    registry.register(_Sample)
    bus = InMemoryEventBus()
    delivered: list[DomainEvent] = []

    async def handler(event: DomainEvent) -> None:
        delivered.append(event)

    bus.subscribe(_Sample, handler)
    repo = _FakeRepo()
    relay, _uow = _relay(repo, registry=registry, bus=bus, now=datetime.now(UTC))

    task = asyncio.create_task(relay.run_forever(0.001))
    repo.seed(_record_for(_Sample(tenant_id=uuid4(), note="first")))
    await _until(lambda: len(delivered) == 1)
    repo.seed(_record_for(_Sample(tenant_id=uuid4(), note="second")))
    await _until(lambda: len(delivered) == 2)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert [e.note for e in delivered if isinstance(e, _Sample)] == ["first", "second"]


async def test_run_forever_survives_a_failing_drain() -> None:
    registry = EventRegistry()
    registry.register(_Sample)
    repo = _FakeRepo()
    relay, _uow = _relay(repo, registry=registry, bus=InMemoryEventBus(), now=datetime.now(UTC))
    calls = 0
    real_claim = repo.claim_pending

    async def flaky(now: datetime, *, limit: int) -> list[OutboxRecord]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database unavailable")
        return await real_claim(now, limit=limit)

    repo.claim_pending = flaky  # type: ignore[method-assign]
    task = asyncio.create_task(relay.run_forever(0.001))
    await _until(lambda: calls >= 3)  # kept going after the first failure
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


async def _until(condition: Callable[[], bool], timeout: float = 2.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while not condition():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.001)
