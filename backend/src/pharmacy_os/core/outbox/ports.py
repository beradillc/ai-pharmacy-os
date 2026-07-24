"""Persistence port for the transactional outbox.

Two callers, two concerns:

* the **Unit of Work** appends a ``PENDING`` row inside the business transaction
  (:meth:`OutboxRepository.add`) — that atomic write is what makes the event durable;
* the **relay** claims due rows (:meth:`claim_pending`) and stamps their outcome
  (:meth:`mark_published` / :meth:`mark_retry` / :meth:`mark_failed`).

There is deliberately no ``delete``: a published or dead-lettered row is kept for
inspection and retention is a separate, explicit sweep (not this port's job).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from pharmacy_os.core.outbox.record import OutboxRecord


class OutboxRepository(Protocol):
    async def add(self, record: OutboxRecord) -> None:
        """Persist a new ``PENDING`` row on the caller's session (business txn)."""
        ...

    async def claim_pending(self, now: datetime, *, limit: int) -> list[OutboxRecord]:
        """Oldest-first ``PENDING`` rows that are due (``next_attempt_at`` null or past).

        Locks the rows it returns (``FOR UPDATE SKIP LOCKED`` on Postgres) so several
        relay instances can drain the same table without handing one event out twice;
        on SQLite the lock clause is a no-op, which is fine for the single-threaded
        test harness.
        """
        ...

    async def mark_published(self, record_id: UUID, published_at: datetime) -> None:
        """Terminal success: the event reached the bus at least once."""
        ...

    async def mark_retry(
        self,
        record_id: UUID,
        *,
        retry_count: int,
        next_attempt_at: datetime,
        last_error: str,
    ) -> None:
        """Stays ``PENDING``; the relay will pick it up again after the backoff."""
        ...

    async def mark_failed(self, record_id: UUID, *, retry_count: int, last_error: str) -> None:
        """Dead-letter: retries exhausted, no further automatic attempts."""
        ...
