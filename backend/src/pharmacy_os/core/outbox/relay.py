"""The outbox relay: drains ``PENDING`` rows and publishes them to the event bus.

**What it guarantees.** An event written to the outbox in a business transaction is
handed to the :class:`~core.events.EventBus` *at least once*, even across a crash
between the business commit and the dispatch. That closes the dual-write window the
plain publish-after-commit Unit of Work leaves open.

**What it does not.** ``InMemoryEventBus.publish`` isolates subscriber failures (logs
and swallows them), so a handler blowing up does **not** fail the drain — the row is
still marked ``PUBLISHED``. Retry/dead-letter here therefore covers *delivery to the
bus* (unknown event type, deserialization, database errors), not subscriber success;
subscriber reliability stays the bus's concern, exactly as before the outbox existed.

**Ordering & concurrency.** Rows are drained oldest-first (by ``occurred_at``).
:meth:`OutboxRepository.claim_pending` locks each batch with ``FOR UPDATE SKIP
LOCKED``, so running several relays (or app instances) never delivers one event twice.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.events import EventBus, EventRegistry, deserialize_event
from pharmacy_os.core.outbox.ports import OutboxRepository
from pharmacy_os.core.outbox.record import OutboxRecord

_log = structlog.get_logger("outbox.relay")

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork], OutboxRepository]
Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class OutboxRelayConfig:
    batch_size: int = 100
    max_retries: int = 5
    base_backoff_seconds: float = 2.0


@dataclass(frozen=True, slots=True)
class DrainResult:
    """Outcome of one :meth:`OutboxRelay.drain_once` pass."""

    published: int = 0
    retried: int = 0
    failed: int = 0

    @property
    def processed(self) -> int:
        return self.published + self.retried + self.failed


def _default_clock() -> datetime:
    return datetime.now(UTC)


class OutboxRelay:
    def __init__(
        self,
        uow_factory: UowFactory,
        repo_factory: RepoFactory,
        event_bus: EventBus,
        registry: EventRegistry,
        config: OutboxRelayConfig | None = None,
        clock: Clock = _default_clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._event_bus = event_bus
        self._registry = registry
        self._config = config or OutboxRelayConfig()
        self._now = clock

    async def drain_once(self) -> DrainResult:
        """Claim one batch of due rows, publish each, stamp the outcome, commit."""
        now = self._now()
        published = retried = failed = 0
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow)
            for record in await repo.claim_pending(now, limit=self._config.batch_size):
                error = await self._publish(record)
                if error is None:
                    await repo.mark_published(record.id, now)
                    published += 1
                elif await self._reschedule(repo, record, error, now):
                    retried += 1
                else:
                    failed += 1
            await uow.commit()
        result = DrainResult(published=published, retried=retried, failed=failed)
        if result.processed:
            _log.info(
                "outbox_drained",
                published=published,
                retried=retried,
                failed=failed,
            )
        return result

    async def _publish(self, record: OutboxRecord) -> str | None:
        """Deliver one record to the bus; return an error string, or ``None`` on success."""
        event_type = self._registry.resolve(record.event_type)
        if event_type is None:
            return f"unknown event_type {record.event_type!r} (not registered)"
        try:
            event = deserialize_event(event_type, record.payload)
            await self._event_bus.publish(event)
        except Exception as exc:  # noqa: BLE001 — any delivery error becomes a retry/dead-letter
            return repr(exc)
        return None

    async def _reschedule(
        self, repo: OutboxRepository, record: OutboxRecord, error: str, now: datetime
    ) -> bool:
        """Bump the attempt count; retry with backoff, or dead-letter when exhausted.

        Returns ``True`` if the row was rescheduled for another try, ``False`` if it
        was moved to ``FAILED``.
        """
        attempt = record.retry_count + 1
        if attempt >= self._config.max_retries:
            await repo.mark_failed(record.id, retry_count=attempt, last_error=error)
            _log.error(
                "outbox_dead_lettered",
                event_id=str(record.event_id),
                event_type=record.event_type,
                retry_count=attempt,
                error=error,
            )
            return False
        backoff = self._config.base_backoff_seconds * 2 ** (attempt - 1)
        await repo.mark_retry(
            record.id,
            retry_count=attempt,
            next_attempt_at=now + timedelta(seconds=backoff),
            last_error=error,
        )
        _log.warning(
            "outbox_retry_scheduled",
            event_id=str(record.event_id),
            event_type=record.event_type,
            retry_count=attempt,
            error=error,
        )
        return True
