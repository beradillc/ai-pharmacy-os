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
from pharmacy_os.modules.clinical.application import CheckInteractionsInput, ClinicalService
from pharmacy_os.modules.clinical.domain import AiContextType
from pharmacy_os.modules.inventory.application import InventoryService, SaleDispenseItem
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.domain import PrescriptionDispensed
from pharmacy_os.modules.sales.domain import DrugInfo, PrescriptionInfo, SaleCompleted

_log = structlog.get_logger("cross_module.sales_inventory")

# The dispense is a system reaction (no end-user request), so it runs under a
# fixed system identity holding exactly the inventory permissions it needs.
_SYSTEM_USER = UUID("00000000-0000-0000-0000-00005a1e5001")
_SYSTEM_PERMISSIONS = frozenset({"inventory.read", "inventory.dispense"})

_safety_log = structlog.get_logger("cross_module.interaction_safety")

# Same system identity, but the interaction check only reads catalog/prescription
# and drives the tenant-gated clinical check — no inventory rights here.
_SAFETY_PERMISSIONS = frozenset({"catalog.read", "rx.read", "clinical.check"})


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


def wire_interaction_safety_check(container: Container) -> None:
    """Subscribe a drug–drug interaction check to sales and dispensing (warn-only).

    A completed sale (``SaleCompleted``) or dispensed prescription
    (``PrescriptionDispensed``) triggers ``clinical.check_interactions`` over the
    basket's active ingredients. Catalog resolves each ``drug_id`` to its ingredients
    (S6 Bước 1); clinical runs the deterministic engine and audits an
    ``AiRecommendation``. This is **warn-only** — both events are post-commit, so the
    sale/dispense is already finalised; blocking-vs-warning is a business/legal call,
    and warn was chosen. Gated per-tenant by ``TenantAiSettings`` (default OFF): a
    tenant that hasn't opted in raises ``FeatureDisabledError``, swallowed silently so
    it isn't logged as a failure. Handler failures are already isolated by the bus.
    """
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]
    clinical = container.resolve(ClinicalService)
    catalog = container.resolve(CatalogService)
    prescription = container.resolve(PrescriptionService)

    async def resolve_ingredient_names(drug_ids: set[UUID], ctx: RequestContext) -> list[str]:
        """Map the basket's drugs to a deduplicated list of active-ingredient names."""
        names: list[str] = []
        seen: set[str] = set()
        for drug_id in drug_ids:
            try:
                refs = await catalog.get_drug_ingredients(drug_id, ctx)
            except NotFoundError:
                continue  # a drug absent from catalog can't be checked; skip it
            for ref in refs:
                key = ref.name.strip().casefold()
                if key not in seen:
                    seen.add(key)
                    names.append(ref.name)
        return names

    async def run_check(
        drug_ids: set[UUID], context_type: AiContextType, context_id: UUID, ctx: RequestContext
    ) -> None:
        names = await resolve_ingredient_names(drug_ids, ctx)
        if len(names) < 2:
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

    async def on_sale_completed(event: DomainEvent) -> None:
        assert isinstance(event, SaleCompleted)
        ctx = RequestContext(
            tenant_id=event.tenant_id,
            branch_id=event.branch_id,
            user_id=_SYSTEM_USER,
            permissions=_SAFETY_PERMISSIONS,
        )
        await run_check({it.drug_id for it in event.items}, AiContextType.SALE, event.order_id, ctx)

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
        await run_check(
            {it.drug_id for it in rx.items}, AiContextType.RX, event.prescription_id, ctx
        )

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
