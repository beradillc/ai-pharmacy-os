"""Cross-module wiring for analytics, at the API composition root.

Analytics never imports sales/inventory/procurement (module-independence); it declares
port shapes and the adapters here implement them over those modules' services. Every
adapter **reads** under a fixed **system identity** holding exactly the permissions that
call needs — so an analytics user needs only the ``analytics.*`` grants, and the
tenant/branch scope comes from the data the analytics service passes in, not from the
caller's token. This mirrors ``cross_module.py``'s system-reaction pattern.

The single **write** (:class:`DraftPoSinkAdapter`) is deliberately different: it runs as
the human who pressed the button, with their own grants — see its docstring.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork, UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.modules.analytics.application import AnalyticsService
from pharmacy_os.modules.analytics.domain import DrugSoldQty
from pharmacy_os.modules.analytics.infrastructure import SqlAlchemyReorderSuggestionRepository
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.procurement.application import (
    CreatePurchaseOrderInput,
    ProcurementService,
    PurchaseOrderItemInput,
)
from pharmacy_os.modules.sales.application import SalesService

# Same convention as cross_module.py: a fixed non-human identity for system reads.
_SYSTEM_USER = UUID("00000000-0000-0000-0000-00005a1e5002")


def _ctx(tenant_id: UUID, branch_id: UUID, permissions: frozenset[str]) -> RequestContext:
    return RequestContext(
        tenant_id=tenant_id, branch_id=branch_id, user_id=_SYSTEM_USER, permissions=permissions
    )


class SalesVelocityAdapter:
    """``SalesVelocitySource`` over ``SalesService`` (reads ``sales.read``)."""

    def __init__(self, sales: SalesService) -> None:
        self._sales = sales

    async def sold_quantity_by_drug(
        self, tenant_id: UUID, branch_id: UUID, *, date_from: object, date_to: object
    ) -> list[DrugSoldQty]:
        ctx = _ctx(tenant_id, branch_id, frozenset({"sales.read"}))
        rows = await self._sales.aggregate_sold_by_drug(
            ctx,
            date_from=date_from,  # type: ignore[arg-type]
            date_to=date_to,  # type: ignore[arg-type]
            branch_id=branch_id,
        )
        return [
            DrugSoldQty(drug_id=r.drug_id, quantity_sold=r.quantity_sold, revenue=r.revenue)
            for r in rows
        ]


class StockLevelAdapter:
    """``StockLevelSource`` over ``InventoryService`` (reads ``inventory.read``)."""

    def __init__(self, inventory: InventoryService) -> None:
        self._inventory = inventory

    async def on_hand_by_drug(self, tenant_id: UUID, branch_id: UUID) -> dict[UUID, Decimal]:
        ctx = _ctx(tenant_id, branch_id, frozenset({"inventory.read"}))
        rows = await self._inventory.on_hand_by_drug(ctx, branch_id=branch_id)
        return {r.drug_id: r.on_hand for r in rows}

    async def count_near_expiry(self, tenant_id: UUID, branch_id: UUID, *, within_days: int) -> int:
        ctx = _ctx(tenant_id, branch_id, frozenset({"inventory.read"}))
        items = await self._inventory.list_near_expiry(ctx, within_days=within_days)
        return len(items)


class DrugNameAdapter:
    """``DrugNameSource`` over ``CatalogService`` (reads ``catalog.read``).

    Catalog is tenant-wide, so branch is the same placeholder ``SupplierAdapter`` uses.

    Running under the **system** identity is the point, not an implementation detail:
    it is what lets a pharmacist holding only ``analytics.read`` see *"Amoxicillin
    500mg"* without also being granted ``catalog.read`` over the whole drug master.
    The names leaked this way are exactly the ones already implied by the numbers on
    the same screen."""

    def __init__(self, catalog: CatalogService) -> None:
        self._catalog = catalog

    async def names_for(self, tenant_id: UUID, drug_ids: Sequence[UUID]) -> dict[UUID, str]:
        ctx = _ctx(tenant_id, tenant_id, frozenset({"catalog.read"}))
        return await self._catalog.drug_names(drug_ids, ctx)


class SupplierAdapter:
    """``SupplierSource`` over ``ProcurementService``.

    Both reads are tenant-wide, so branch is a placeholder (the tenant id) — the same
    stand-in ``cross_module.py`` uses for branch-less system reads. Each call carries
    **only** the grant it needs (``procurement.po.read`` to pick a supplier,
    ``procurement.supplier.read`` to label one), not the union of both."""

    def __init__(self, procurement: ProcurementService) -> None:
        self._procurement = procurement

    async def last_supplier_for_drug(self, tenant_id: UUID, drug_id: UUID) -> UUID | None:
        ctx = _ctx(tenant_id, tenant_id, frozenset({"procurement.po.read"}))
        return await self._procurement.last_supplier_for_drug(drug_id, ctx)

    async def names_for(self, tenant_id: UUID, supplier_ids: Sequence[UUID]) -> dict[UUID, str]:
        ctx = _ctx(tenant_id, tenant_id, frozenset({"procurement.supplier.read"}))
        return await self._procurement.supplier_names(supplier_ids, ctx)


class DraftPoCountAdapter:
    """``DraftPoCountSource`` over ``ProcurementService`` (reads ``procurement.po.read``)."""

    def __init__(self, procurement: ProcurementService) -> None:
        self._procurement = procurement

    async def count_draft_pos(self, tenant_id: UUID, branch_id: UUID) -> int:
        ctx = _ctx(tenant_id, branch_id, frozenset({"procurement.po.read"}))
        return await self._procurement.count_draft_purchase_orders(ctx, branch_id=branch_id)


class DraftPoSinkAdapter:
    """``DraftPoSink`` over ``ProcurementService`` (writes via ``procurement.po.create``).

    Creates a single-line DRAFT PO with ``unit_price = 0``: analytics forecasts demand,
    not price — the human fills the quote in on the draft before placing it.

    The **only** adapter here that does not use the system identity: it runs as the
    human who pressed materialise, with exactly their grants (design doc §6). So a role
    holding ``analytics.reorder.run`` but not ``procurement.po.create`` is refused by
    procurement itself — analytics is not a side door into creating purchase orders."""

    def __init__(self, procurement: ProcurementService) -> None:
        self._procurement = procurement

    async def create_draft_po(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        actor_user_id: UUID,
        actor_permissions: frozenset[str],
        supplier_id: UUID,
        drug_id: UUID,
        quantity: Decimal,
    ) -> UUID:
        ctx = RequestContext(
            tenant_id=tenant_id,
            branch_id=branch_id,
            user_id=actor_user_id,
            permissions=actor_permissions,
        )
        out = await self._procurement.create_purchase_order(
            CreatePurchaseOrderInput(
                supplier_id=supplier_id,
                items=[
                    PurchaseOrderItemInput(
                        drug_id=drug_id, quantity_ordered=quantity, unit_price=Decimal("0")
                    )
                ],
            ),
            ctx,
        )
        return out.id


def wire_analytics(container: Container) -> None:
    """Build ``AnalyticsService`` from adapters over the other modules and register it.

    Called after sales/inventory/procurement are registered (they must already be in
    the container). Reorder policy defaults (90-day window, 7-day lead, 3-day safety)
    are the tenant defaults; per-tenant override is deferred (PROJECT_STATE §7am Q2)."""
    uow_factory = container.resolve(UnitOfWorkFactory)
    sales = container.resolve(SalesService)
    inventory = container.resolve(InventoryService)
    procurement = container.resolve(ProcurementService)
    catalog = container.resolve(CatalogService)

    def repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemyReorderSuggestionRepository:
        return SqlAlchemyReorderSuggestionRepository(uow.session, ctx)

    service = AnalyticsService(
        uow_factory,
        repo_factory,
        SalesVelocityAdapter(sales),
        StockLevelAdapter(inventory),
        SupplierAdapter(procurement),
        DraftPoCountAdapter(procurement),
        DraftPoSinkAdapter(procurement),
        DrugNameAdapter(catalog),
        container.resolve(AuditLogger),
    )
    container.register_instance(AnalyticsService, service)
