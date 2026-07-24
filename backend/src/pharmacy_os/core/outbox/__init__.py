"""Transactional outbox: durable at-least-once publication of domain events.

An event is written to the ``event_outbox`` table inside the same transaction as the
business data that produced it, then the :class:`OutboxRelay` delivers it to the event
bus — so an event is never lost between a successful business commit and its dispatch.
"""

from pharmacy_os.core.outbox.ports import OutboxRepository
from pharmacy_os.core.outbox.record import OutboxRecord, OutboxStatus
from pharmacy_os.core.outbox.relay import (
    DrainResult,
    OutboxRelay,
    OutboxRelayConfig,
)
from pharmacy_os.core.outbox.repository import SqlAlchemyOutboxRepository

__all__ = [
    "DrainResult",
    "OutboxRecord",
    "OutboxRelay",
    "OutboxRelayConfig",
    "OutboxRepository",
    "OutboxStatus",
    "SqlAlchemyOutboxRepository",
]
