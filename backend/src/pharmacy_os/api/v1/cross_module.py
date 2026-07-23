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
from pharmacy_os.core.errors import FeatureDisabledError, NotFoundError
from pharmacy_os.core.events import DomainEvent, EventBus
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.clinical.application import (
    BasketIngredient,
    CheckAllergiesInput,
    CheckInteractionsInput,
    ClinicalService,
)
from pharmacy_os.modules.clinical.domain import AiContextType
from pharmacy_os.modules.crm.application import CrmService
from pharmacy_os.modules.inventory.application import (
    GoodsReceiptLine,
    InventoryService,
    SaleDispenseItem,
)
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.domain import PrescriptionDispensed
from pharmacy_os.modules.procurement.domain import GoodsReceived
from pharmacy_os.modules.sales.domain import DrugInfo, PrescriptionInfo, SaleCompleted

_log = structlog.get_logger("cross_module.sales_inventory")

# The dispense is a system reaction (no end-user request), so it runs under a
# fixed system identity holding exactly the inventory permissions it needs.
_SYSTEM_USER = UUID("00000000-0000-0000-0000-00005a1e5001")
_SYSTEM_PERMISSIONS = frozenset({"inventory.read", "inventory.dispense"})

_grn_log = structlog.get_logger("cross_module.goods_receipt_inventory")
# Stock-in from a confirmed GRN needs only the receive right.
_GRN_STOCK_IN_PERMISSIONS = frozenset({"inventory.receive"})

_safety_log = structlog.get_logger("cross_module.safety_checks")

# Same system identity, but the safety checks only read catalog/prescription/crm
# and drive the clinical checks — no inventory rights here.
_SAFETY_PERMISSIONS = frozenset({"catalog.read", "rx.read", "crm.read", "clinical.check"})


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


def wire_goods_receipt_stock_in(container: Container) -> None:
    """Subscribe inventory stock-in to procurement's ``GoodsReceived``.

    A confirmed goods-receipt note creates one inventory ``ProductBatch`` (+ IN
    movement) per received line, idempotent on ``grn_id``. Lot collisions and any
    other failures are recorded in ``stock_reconciliation_needed`` by the use-case
    rather than blocking — the GRN is already committed. This mirrors
    ``wire_sale_dispensing``; ``procurement`` and ``inventory`` never import each
    other, the link lives here and maps ``ReceivedItem`` onto inventory's own
    ``GoodsReceiptLine``.
    """
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    inventory = container.resolve(InventoryService)

    async def on_goods_received(event: DomainEvent) -> None:
        assert isinstance(event, GoodsReceived)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_GRN_STOCK_IN_PERMISSIONS,
        )
        lines = [
            GoodsReceiptLine(
                drug_id=it.drug_id,
                lot_no=it.lot_no,
                expiry_date=it.expiry_date,
                unit_cost=it.unit_cost,
                quantity=it.quantity,
                po_item_id=it.po_item_id,
                mfg_date=it.mfg_date,
            )
            for it in event.items
        ]
        await inventory.receive_from_goods_receipt(lines, event.grn_id, ctx)
        _grn_log.info("grn_stock_in", grn_id=str(event.grn_id), lines=len(lines))

    event_bus.subscribe(GoodsReceived, on_goods_received)


def wire_safety_checks(container: Container) -> None:
    """Subscribe the clinical safety checks to sales and dispensing (warn-only).

    A completed sale (``SaleCompleted``) or dispensed prescription
    (``PrescriptionDispensed``) is resolved to its basket of active ingredients via
    catalog (S6 Bước 1), then run through:

    * **Interactions** (both events) — ``clinical.check_interactions`` over the
      ingredient names; deterministic engine + audited ``AiRecommendation``. Gated
      per-tenant by ``TenantAiSettings`` (default OFF): an unopted tenant raises
      ``FeatureDisabledError``, swallowed silently.
    * **Allergies** (dispensing only — a prescription carries the ``customer_id``) —
      ``clinical.check_allergies`` matching the basket against the customer's recorded
      allergies (read from crm). Deterministic and **not** tenant-gated: it runs for
      every tenant.

    All **warn-only** — both events are post-commit, so the sale/dispense is already
    finalised; blocking-vs-warning is a business/legal call and warn was chosen.
    Handler failures are already isolated by the bus.
    """
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    clinical = container.resolve(ClinicalService)
    catalog = container.resolve(CatalogService)
    crm = container.resolve(CrmService)
    prescription = container.resolve(PrescriptionService)

    async def resolve_basket(drug_ids: set[UUID], ctx: RequestContext) -> list[tuple[UUID, str]]:
        """Map the basket's drugs to deduplicated ``(ingredient_id, name)`` pairs."""
        basket: list[tuple[UUID, str]] = []
        seen: set[UUID] = set()
        for drug_id in drug_ids:
            try:
                refs = await catalog.get_drug_ingredients(drug_id, ctx)
            except NotFoundError:
                continue  # a drug absent from catalog can't be checked; skip it
            for ref in refs:
                if ref.ingredient_id not in seen:
                    seen.add(ref.ingredient_id)
                    basket.append((ref.ingredient_id, ref.name))
        return basket

    async def run_interaction_check(
        basket: list[tuple[UUID, str]],
        context_type: AiContextType,
        context_id: UUID,
        ctx: RequestContext,
    ) -> None:
        names = [name for _, name in basket]
        if len({name.strip().casefold() for name in names}) < 2:
            return  # no drug–drug interaction possible; skip to avoid empty audit noise
        try:
            result = await clinical.check_interactions(
                CheckInteractionsInput(
                    ingredients=names, context_type=context_type, context_id=context_id
                ),
                ctx,
            )
        except FeatureDisabledError:
            return  # tenant hasn't opted into clinical AI — a normal state, stay silent
        if result.recommendation.requires_review:
            _safety_log.warning(
                "interaction_warning_raised",
                context_type=context_type.value,
                context_id=str(context_id),
                findings=len(result.findings),
            )

    async def run_allergy_check(
        basket: list[tuple[UUID, str]],
        customer_id: UUID,
        context_id: UUID,
        ctx: RequestContext,
    ) -> None:
        try:
            customer = await crm.get_customer(customer_id, ctx)
        except NotFoundError:
            return  # customer record gone; nothing to match against
        severities = {a.ingredient_id: a.severity for a in customer.allergies}
        if not severities:
            return
        result = await clinical.check_allergies(
            CheckAllergiesInput(
                basket=[BasketIngredient(ingredient_id=i, name=n) for i, n in basket],
                allergy_severities=severities,
                context_id=context_id,
            ),
            ctx,
        )
        if result.alerts:
            _safety_log.warning(
                "allergy_warning_raised",
                context_id=str(context_id),
                customer_id=str(customer_id),
                alerts=len(result.alerts),
            )

    async def on_sale_completed(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_SAFETY_PERMISSIONS,
        )
        basket = await resolve_basket({it.drug_id for it in event.items}, ctx)
        # OTC sales carry no customer_id, so only the drug–drug check runs here.
        await run_interaction_check(basket, AiContextType.SALE, event.order_id, ctx)

    async def on_prescription_dispensed(event: DomainEvent) -> None:
        assert isinstance(event, PrescriptionDispensed)
        # PrescriptionDispensed carries no branch_id; use the tenant as the branch
        # scope (same placeholder the read adapters above use for system reactions).
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.tenant_id,
            user_id=_SYSTEM_USER,
            permissions=_SAFETY_PERMISSIONS,
        )
        try:
            rx = await prescription.get_prescription(event.prescription_id, ctx)
        except NotFoundError:
            return
        basket = await resolve_basket({it.drug_id for it in rx.items}, ctx)
        await run_interaction_check(basket, AiContextType.RX, event.prescription_id, ctx)
        await run_allergy_check(basket, rx.customer_id, event.prescription_id, ctx)

    event_bus.subscribe(SaleCompleted, on_sale_completed)
    event_bus.subscribe(PrescriptionDispensed, on_prescription_dispensed)


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
        return DrugInfo(
            drug_id=drug_id,
            requires_prescription=drug.prescription_required,
            name=drug.name,
            unit=drug.base_unit,
        )


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
