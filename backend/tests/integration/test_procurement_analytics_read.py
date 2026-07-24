"""Procurement reads for analytics: DRAFT PO count (dashboard tile) and
last-supplier-for-a-drug (how a reorder suggestion picks its supplier, Q3).
PROJECT_STATE §7am.
"""

from decimal import Decimal
from uuid import uuid4

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.procurement.application import (
    CreatePurchaseOrderInput,
    CreateSupplierInput,
    ProcurementService,
    PurchaseOrderItemInput,
)


async def _po(
    svc: ProcurementService, ctx: RequestContext, supplier_id: object, drug_id: object
) -> object:
    return await svc.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier_id,  # type: ignore[arg-type]
            items=[
                PurchaseOrderItemInput(
                    drug_id=drug_id,  # type: ignore[arg-type]
                    quantity_ordered=Decimal("10"),
                    unit_price=Decimal("1000"),
                )
            ],
        ),
        ctx,
    )


async def test_count_draft_purchase_orders(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC"), ctx)
    assert await procurement_service.count_draft_purchase_orders(ctx) == 0

    await _po(procurement_service, ctx, supplier.id, uuid4())
    await _po(procurement_service, ctx, supplier.id, uuid4())
    assert await procurement_service.count_draft_purchase_orders(ctx) == 2


async def test_placed_po_is_not_counted_as_draft(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC"), ctx)
    po = await _po(procurement_service, ctx, supplier.id, uuid4())
    await procurement_service.mark_ordered(po.id, ctx)  # type: ignore[attr-defined]
    assert await procurement_service.count_draft_purchase_orders(ctx) == 0


async def test_last_supplier_for_drug_uses_most_recent_placed_po(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    drug = uuid4()
    ncc1 = await procurement_service.create_supplier(CreateSupplierInput(name="NCC 1"), ctx)
    ncc2 = await procurement_service.create_supplier(CreateSupplierInput(name="NCC 2"), ctx)

    po1 = await _po(procurement_service, ctx, ncc1.id, drug)
    await procurement_service.mark_ordered(po1.id, ctx)  # type: ignore[attr-defined]
    po2 = await _po(procurement_service, ctx, ncc2.id, drug)
    await procurement_service.mark_ordered(po2.id, ctx)  # type: ignore[attr-defined]

    assert await procurement_service.last_supplier_for_drug(drug, ctx) == ncc2.id


async def test_last_supplier_ignores_draft_only_history(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    drug = uuid4()
    ncc = await procurement_service.create_supplier(CreateSupplierInput(name="NCC"), ctx)
    await _po(procurement_service, ctx, ncc.id, drug)  # left DRAFT, never placed
    assert await procurement_service.last_supplier_for_drug(drug, ctx) is None


async def test_last_supplier_none_for_never_ordered_drug(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    assert await procurement_service.last_supplier_for_drug(uuid4(), ctx) is None
