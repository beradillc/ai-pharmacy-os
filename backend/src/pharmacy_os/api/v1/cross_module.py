"""Cross-module wiring lives here, at the API composition root.

Business modules never import one another (the ``module-independence``
contract). When one module must react to another's event, the subscription is
declared here — the ``api`` layer is allowed to depend on any module. This is
the first such link: a completed sale drives an inventory dispense (FEFO).
"""

from __future__ import annotations

from uuid import UUID

import structlog

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.di import Container
from pharmacy_os.core.errors import NotFoundError
from pharmacy_os.core.events import DomainEvent, EventBus
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.inventory.application import InventoryService, SaleDispenseItem
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.sales.domain import DrugInfo, PrescriptionInfo, SaleCompleted

_log = structlog.get_logger("cross_module.sales_inventory")

# The dispense is a system reaction (no end-user request), so it runs under a
# fixed system identity holding exactly the inventory permissions it needs.
_SYSTEM_USER = UUID("00000000-0000-0000-0000-00005a1e5001")
_SYSTEM_PERMISSIONS = frozenset({"inventory.read", "inventory.dispense"})


def wire_sale_dispensing(container: Container) -> None:
    """Subscribe inventory dispensing to ``SaleCompleted``."""
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    inventory = container.resolve(InventoryService)

    async def on_sale_completed(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_SYSTEM_PERMISSIONS,
        )
        items = [SaleDispenseItem(drug_id=it.drug_id, quantity=it.quantity) for it in event.items]
        await inventory.dispense_for_sale(items, event.order_id, ctx)
        _log.info("sale_dispensed", order_id=str(event.order_id), lines=len(items))

    event_bus.subscribe(SaleCompleted, on_sale_completed)


class CatalogDrugInfoProvider:
    """Adapter making catalog the authority for a sale's Rx status.

    Implements the sales ``DrugInfoProvider`` port over ``CatalogService`` — the
    dependency lives here in ``api`` so sales never imports catalog.
    """

    def __init__(self, catalog: CatalogService) -> None:
        self._catalog = catalog

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugInfo | None:
        ctx = RequestContext(
            tenant_id=tenant_id,
            branch_id=tenant_id,
            user_id=_SYSTEM_USER,
            permissions=frozenset({"catalog.read"}),
        )
        try:
            drug = await self._catalog.get_drug(drug_id, ctx)
        except NotFoundError:
            return None
        return DrugInfo(drug_id=drug_id, requires_prescription=drug.prescription_required)


class PrescriptionInfoAdapter:
    """Adapter making prescription the authority for a sale's ``prescription_ref``.

    Implements the sales ``PrescriptionInfoProvider`` port over ``PrescriptionService``
    — the dependency lives here in ``api`` so sales never imports prescription. Lets
    ``complete_sale`` verify an ETC order's ref is a real, sale-authorising Rx (S5.4).
    """

    def __init__(self, prescription: PrescriptionService) -> None:
        self._prescription = prescription

    async def get(self, prescription_id: UUID, tenant_id: UUID) -> PrescriptionInfo | None:
        ctx = RequestContext(
            tenant_id=tenant_id,
            branch_id=tenant_id,
            user_id=_SYSTEM_USER,
            permissions=frozenset({"rx.read"}),
        )
        try:
            rx = await self._prescription.get_prescription(prescription_id, ctx)
        except NotFoundError:
            return None
        return PrescriptionInfo(prescription_id=prescription_id, status=rx.status)
