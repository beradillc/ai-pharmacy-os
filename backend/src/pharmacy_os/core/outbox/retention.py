"""Retention: delete finished outbox rows so the table stops growing forever.

Every business write now adds rows to ``event_outbox`` (a single sale produces three or
more), and nothing ever removed them. Left alone the table outgrows the data it
describes, and the relay's own dispatch query slows down with it.

**What is safe to delete, and what is not.**

* ``PUBLISHED`` — delivered at least once. The business record it announced lives in its
  own table (``sales_orders``, ``stock_movements``, …) and the audit trail lives in
  ``audit_logs``; an outbox row is delivery plumbing, not evidence, so ageing it out
  destroys nothing an inspection would ask for.
* ``FAILED`` — a dead letter nobody has looked at yet. Kept **forever by default**
  (``failed_after_days=None``): deleting it silently discards the one trace that
  something never got delivered. Set a window only if the deployment has a real process
  for reviewing dead letters.
* ``PENDING`` — never, at any age. It is undelivered work; the type of
  :meth:`~pharmacy_os.core.outbox.ports.OutboxRepository.purge_terminal` makes asking
  for it impossible.

Runs on its own slow schedule, independent of the relay: rows accumulate under
``OUTBOX__SYNC_DRAIN`` just as they do under the async relay, so retention must not be
tied to whether the relay is enabled.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog

from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.outbox.ports import OutboxRepository, TerminalStatus
from pharmacy_os.core.outbox.record import OutboxStatus

_log = structlog.get_logger("outbox.retention")

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork], OutboxRepository]
Clock = Callable[[], datetime]


@dataclass(frozen=True, slots=True)
class OutboxRetentionConfig:
    published_after_days: int = 30
    """Age at which a delivered row is dropped."""

    failed_after_days: int | None = None
    """Age at which a dead letter is dropped; ``None`` keeps dead letters forever."""

    batch_size: int = 500
    """Rows per transaction — small enough that a sweep never holds a long lock."""

    max_batches: int = 20
    """Cap per sweep. A huge backlog is cleared over several sweeps rather than in one
    transaction storm; the next run continues where this one stopped."""


@dataclass(frozen=True, slots=True)
class PurgeResult:
    published: int = 0
    failed: int = 0

    @property
    def deleted(self) -> int:
        return self.published + self.failed


def _default_clock() -> datetime:
    return datetime.now(UTC)


class OutboxRetention:
    def __init__(
        self,
        uow_factory: UowFactory,
        repo_factory: RepoFactory,
        config: OutboxRetentionConfig | None = None,
        clock: Clock = _default_clock,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._config = config or OutboxRetentionConfig()
        self._now = clock

    async def purge_once(self) -> PurgeResult:
        """One sweep: age out delivered rows, and dead letters if a window is set."""
        published = await self._purge(OutboxStatus.PUBLISHED, self._config.published_after_days)
        failed = 0
        if self._config.failed_after_days is not None:
            failed = await self._purge(OutboxStatus.FAILED, self._config.failed_after_days)
        result = PurgeResult(published=published, failed=failed)
        if result.deleted:
            _log.info("outbox_purged", published=published, failed=failed)
        return result

    async def run_forever(self, interval_seconds: float) -> None:
        """Sweep in a loop until cancelled; a failed sweep is retried next tick."""
        while True:
            try:
                await self.purge_once()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 — a failed sweep must not stop the loop
                _log.exception("outbox_purge_failed")
            await asyncio.sleep(interval_seconds)

    async def _purge(self, status: TerminalStatus, after_days: int) -> int:
        cutoff = self._now() - timedelta(days=after_days)
        total = 0
        for _batch in range(self._config.max_batches):
            async with self._uow_factory() as uow:
                deleted = await self._repo_factory(uow).purge_terminal(
                    status, older_than=cutoff, limit=self._config.batch_size
                )
                await uow.commit()
            total += deleted
            if deleted < self._config.batch_size:
                break  # drained: this batch was the last one
        return total
