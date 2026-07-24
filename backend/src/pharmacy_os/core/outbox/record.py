"""What an outbox row is: one recorded domain event awaiting publication.

Framework-free on purpose (mirrors ``core.audit.entry``): the same shape is written
to the ``event_outbox`` table, claimed by the relay, and marked published/failed. The
``payload`` is already the JSON-safe dict that :func:`core.events.serialize_event`
produces — this type does **not** know the codec, so it stays free of any event class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4


class OutboxStatus(StrEnum):
    """Lifecycle of an outbox row.

    ``PENDING`` — written in the business transaction, not yet handed to the bus.
    ``PUBLISHED`` — the relay delivered it to the bus at least once.
    ``FAILED`` — dead-letter: exhausted ``max_retries``, needs a human to look.
    """

    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    """One event captured for at-least-once delivery.

    ``event_id`` is the :class:`~core.events.DomainEvent`'s own id (unique in the
    table): re-collecting the same event writes one row, and a consumer can dedupe on
    it. ``id`` is the row's own key, distinct from the event it carries.

    ``occurred_at`` is the event's business time and drives the relay's delivery order
    (oldest first). ``retry_count`` / ``next_attempt_at`` / ``last_error`` are the
    relay's bookkeeping and are meaningless until a first delivery attempt fails.
    """

    event_id: UUID
    event_type: str
    tenant_id: UUID
    payload: dict[str, Any]
    occurred_at: datetime
    status: OutboxStatus = OutboxStatus.PENDING
    retry_count: int = 0
    next_attempt_at: datetime | None = None
    published_at: datetime | None = None
    last_error: str | None = None
    id: UUID = field(default_factory=uuid4)

    @classmethod
    def pending(
        cls,
        *,
        event_id: UUID,
        event_type: str,
        tenant_id: UUID,
        payload: dict[str, Any],
        occurred_at: datetime,
    ) -> OutboxRecord:
        """A fresh ``PENDING`` row for a serialized event (the only way one is born)."""
        return cls(
            event_id=event_id,
            event_type=event_type,
            tenant_id=tenant_id,
            payload=payload,
            occurred_at=occurred_at,
        )
