"""Cross-module wiring: a completed sale enqueues a national-DB sync push.

Declared at the API composition root (the ``module-independence`` contract:
business modules never import one another). Compliance only reacts to the
already-published :class:`SaleCompleted` and drives its own
:class:`NationalSyncService` — it imports nothing from sales beyond the event class,
exactly like :func:`wire_sale_dispensing`.

Design 5a scope: this link ONLY enqueues a ``NationalSyncLog`` (idempotent by
``client_uuid``). It deliberately does NOT write a ``ControlledLedgerEntry``:
``SaleCompleted`` carries none of the legally required category / lot / customer /
prescription fields, and providing them would mean either changing the sales
contract or adding cross-module read-ports. The ledger therefore stays an explicit
use-case (``ComplianceService.record_controlled_entry``), captured where that data
actually exists.
"""

from __future__ import annotations

import json
from uuid import UUID

import structlog

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import DomainEvent, EventBus
from pharmacy_os.modules.compliance.application import NationalSyncService, PushSyncInput
from pharmacy_os.modules.compliance.domain import SyncPayloadType
from pharmacy_os.modules.sales.domain import SaleCompleted

_log = structlog.get_logger("cross_module.sales_compliance")

# The sync push is a system reaction (no end-user request), so it runs under a
# fixed system identity holding exactly the sync permission it needs.
_SYSTEM_USER = UUID("00000000-0000-0000-0000-00005a1e5c05")
_SYSTEM_PERMISSIONS = frozenset({"compliance.sync.push"})


def _serialize_sale(event: SaleCompleted) -> str:
    """Deterministic payload for the sync push; only its hash is persisted."""
    return json.dumps(
        {
            "order_id": str(event.order_id),
            "client_uuid": event.client_uuid,
            "items": [
                {"drug_id": str(item.drug_id), "quantity": str(item.quantity)}
                for item in event.items
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def wire_compliance_sync(container: Container) -> None:
    """Subscribe a national-DB sync push to ``SaleCompleted``."""
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    national_sync = container.resolve(NationalSyncService)

    async def on_sale_completed(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_SYSTEM_PERMISSIONS,
        )
        # Idempotent by client_uuid: a replayed SaleCompleted reuses the same log
        # (an already-ACKed one is returned untouched), never a duplicate push.
        await national_sync.push_payload(
            PushSyncInput(
                payload_type=SyncPayloadType.SALE,
                client_uuid=event.client_uuid,
                payload=_serialize_sale(event),
            ),
            ctx,
        )
        _log.info(
            "sale_sync_enqueued",
            order_id=str(event.order_id),
            client_uuid=event.client_uuid,
        )

    event_bus.subscribe(SaleCompleted, on_sale_completed)
