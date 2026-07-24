"""Composition-root wiring for the transactional outbox.

The kernel deliberately does not know which domain events exist (``core`` must not
import business modules), but the relay has to turn a stored ``event_type`` name back
into a class before it can publish. That mapping is membership, not mechanism, so it
belongs here in ``api`` — the one layer allowed to see every module.

Adding a new :class:`DomainEvent` therefore means adding it to :data:`ALL_EVENTS`.
Forgetting is caught by ``tests/unit/test_outbox_registry.py``, not at runtime — an
unregistered event would sit in the outbox retrying until it dead-letters.
"""

from __future__ import annotations

import structlog

from pharmacy_os.core.config import Settings
from pharmacy_os.core.db import UnitOfWork, UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import DomainEvent, EventBus, EventRegistry
from pharmacy_os.core.outbox import (
    OutboxRelay,
    OutboxRelayConfig,
    SqlAlchemyOutboxRepository,
)
from pharmacy_os.modules.iam.domain import RolesChanged, UserDeactivated, UserRegistered
from pharmacy_os.modules.inventory.domain import (
    LowStockDetected,
    StockMovedIn,
    StockMovedOut,
    StockShortfallDetected,
)
from pharmacy_os.modules.prescription.domain import (
    PrescriptionDispensed,
    PrescriptionRejected,
    PrescriptionValidated,
)
from pharmacy_os.modules.procurement.domain import GoodsReceived, PurchaseOrdered
from pharmacy_os.modules.sales.domain import SaleCompleted, SaleReturned

_log = structlog.get_logger("outbox.wiring")

ALL_EVENTS: tuple[type[DomainEvent], ...] = (
    SaleCompleted,
    SaleReturned,
    PrescriptionValidated,
    PrescriptionRejected,
    PrescriptionDispensed,
    PurchaseOrdered,
    GoodsReceived,
    StockMovedIn,
    StockMovedOut,
    LowStockDetected,
    StockShortfallDetected,
    UserRegistered,
    RolesChanged,
    UserDeactivated,
)


def _outbox_repo(uow: UnitOfWork) -> SqlAlchemyOutboxRepository:
    return SqlAlchemyOutboxRepository(uow.session)


def wire_outbox(container: Container) -> None:
    """Register the event registry and the relay that drains ``event_outbox``.

    Only registration — the relay is *started* by the app lifespan (``main._lifespan``)
    when ``OUTBOX__RELAY_ENABLED`` is on, because a background poller has to be tied to
    the process's lifetime, not to router construction.
    """
    registry = EventRegistry()
    registry.register(*ALL_EVENTS)
    container.register_instance(EventRegistry, registry)

    settings = container.resolve(Settings)
    uow_factory = container.resolve(UnitOfWorkFactory)
    relay = OutboxRelay(
        uow_factory,
        _outbox_repo,
        container.resolve(EventBus),  # type: ignore[type-abstract]
        registry,
        OutboxRelayConfig(
            batch_size=settings.outbox.batch_size,
            max_retries=settings.outbox.max_retries,
            base_backoff_seconds=settings.outbox.base_backoff_seconds,
        ),
    )
    container.register_instance(OutboxRelay, relay)

    if settings.app.env == "prod" and not settings.outbox.relay_enabled:
        _log.warning(
            "outbox_relay_disabled_in_prod",
            detail=(
                "events left PENDING by a crash between commit and publish will not be "
                "redelivered — set OUTBOX__RELAY_ENABLED=true"
            ),
        )


__all__ = ["ALL_EVENTS", "wire_outbox"]
