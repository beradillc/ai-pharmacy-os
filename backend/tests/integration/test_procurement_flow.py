from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from pharmacy_os.core.events import DomainEvent, InMemoryEventBus
from pharmacy_os.modules.procurement.application import (
    CreateGoodsReceiptInput,
    CreatePurchaseOrderInput,
    CreateSupplierInput,
    GoodsReceiptItemInput,
    ProcurementService,
    PurchaseOrderItemInput,
)
from pharmacy_os.modules.procurement.domain import (
    GoodsReceived,
    PurchaseOrdered,
    PurchaseOrderStatus,
)


def _expiry(days: int = 365) -> date:
    return date.today() + timedelta(days=days)


async def test_create_and_get_supplier(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    created = await procurement_service.create_supplier(
        CreateSupplierInput(name="Dược Trung Ương", tax_code="0100100100"), ctx
    )
    assert created.is_active is True

    fetched = await procurement_service.get_supplier(created.id, ctx)
    assert fetched.name == "Dược Trung Ương"


async def test_supplier_tenant_isolation(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    created = await procurement_service.create_supplier(CreateSupplierInput(name="X"), ctx)
    other = RequestContext(
        tenant_id=uuid4(), branch_id=ctx.branch_id, user_id=ctx.user_id, permissions=ctx.permissions
    )
    with pytest.raises(NotFoundError):
        await procurement_service.get_supplier(created.id, other)


async def test_supplier_permission_enforced(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    no_perm = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset(),
    )
    with pytest.raises(PermissionDeniedError):
        await procurement_service.create_supplier(CreateSupplierInput(name="Y"), no_perm)


async def test_list_suppliers_ordered_by_name(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    await procurement_service.create_supplier(CreateSupplierInput(name="Bình"), ctx)
    await procurement_service.create_supplier(CreateSupplierInput(name="An"), ctx)
    items = await procurement_service.list_suppliers(ctx)
    assert [s.name for s in items] == ["An", "Bình"]


async def test_get_unknown_supplier_404(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await procurement_service.get_supplier(uuid4(), ctx)


async def test_invalid_supplier_name_rejected(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    with pytest.raises(ValidationError):
        await procurement_service.create_supplier(CreateSupplierInput(name="  "), ctx)


async def test_create_purchase_order_with_items_and_get(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC A"), ctx)
    drug_id = uuid4()
    created = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=drug_id, quantity_ordered=Decimal("100"), unit_price=Decimal("5000")
                )
            ],
        ),
        ctx,
    )
    assert created.status == PurchaseOrderStatus.DRAFT.value
    assert len(created.items) == 1

    fetched = await procurement_service.get_purchase_order(created.id, ctx)
    assert fetched.supplier_id == supplier.id
    assert fetched.items[0].drug_id == drug_id


async def test_add_po_item_while_draft(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC B"), ctx)
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(supplier_id=supplier.id), ctx
    )
    updated = await procurement_service.add_po_item(
        po.id,
        PurchaseOrderItemInput(
            drug_id=uuid4(), quantity_ordered=Decimal("10"), unit_price=Decimal("1000")
        ),
        ctx,
    )
    assert len(updated.items) == 1


async def test_mark_ordered_emits_event_and_blocks_add_item(
    procurement_service: ProcurementService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    events: list[PurchaseOrdered] = []

    async def on_ordered(event: DomainEvent) -> None:
        assert isinstance(event, PurchaseOrdered)
        events.append(event)

    event_bus.subscribe(PurchaseOrdered, on_ordered)

    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC C"), ctx)
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=uuid4(), quantity_ordered=Decimal("10"), unit_price=Decimal("1000")
                )
            ],
        ),
        ctx,
    )
    ordered = await procurement_service.mark_ordered(po.id, ctx)
    assert ordered.status == PurchaseOrderStatus.ORDERED.value
    assert len(events) == 1
    assert events[0].po_id == po.id

    with pytest.raises(ValidationError):
        await procurement_service.add_po_item(
            po.id,
            PurchaseOrderItemInput(
                drug_id=uuid4(), quantity_ordered=Decimal("1"), unit_price=Decimal("1")
            ),
            ctx,
        )


async def test_place_order_empty_rejected(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC D"), ctx)
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(supplier_id=supplier.id), ctx
    )
    with pytest.raises(ValidationError):
        await procurement_service.mark_ordered(po.id, ctx)


async def test_cancel_from_draft(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC E"), ctx)
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(supplier_id=supplier.id), ctx
    )
    cancelled = await procurement_service.cancel_purchase_order(po.id, ctx)
    assert cancelled.status == PurchaseOrderStatus.CANCELLED.value


async def test_cancel_after_ordered_rejected(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC F"), ctx)
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=uuid4(), quantity_ordered=Decimal("10"), unit_price=Decimal("1000")
                )
            ],
        ),
        ctx,
    )
    await procurement_service.mark_ordered(po.id, ctx)
    with pytest.raises(ValidationError):
        await procurement_service.cancel_purchase_order(po.id, ctx)


async def test_confirm_partial_receipt_sets_partially_received(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC G"), ctx)
    drug_id = uuid4()
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=drug_id, quantity_ordered=Decimal("100"), unit_price=Decimal("5000")
                )
            ],
        ),
        ctx,
    )
    ordered = await procurement_service.mark_ordered(po.id, ctx)
    grn = await procurement_service.create_goods_receipt(
        CreateGoodsReceiptInput(
            po_id=ordered.id,
            items=[
                GoodsReceiptItemInput(
                    po_item_id=ordered.items[0].id,
                    drug_id=drug_id,
                    quantity_received=Decimal("40"),
                    lot_no="LOT001",
                    expiry_date=_expiry(),
                    unit_cost=Decimal("4800"),
                )
            ],
        ),
        ctx,
    )
    confirmed = await procurement_service.confirm_goods_receipt(grn.id, ctx)
    assert confirmed.status == "CONFIRMED"

    updated_po = await procurement_service.get_purchase_order(ordered.id, ctx)
    assert updated_po.status == PurchaseOrderStatus.PARTIALLY_RECEIVED.value
    assert updated_po.items[0].quantity_received == Decimal("40")


async def test_confirm_full_receipt_sets_received_and_emits_event(
    procurement_service: ProcurementService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    events: list[GoodsReceived] = []

    async def on_received(event: DomainEvent) -> None:
        assert isinstance(event, GoodsReceived)
        events.append(event)

    event_bus.subscribe(GoodsReceived, on_received)

    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC H"), ctx)
    drug_id = uuid4()
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=drug_id, quantity_ordered=Decimal("100"), unit_price=Decimal("5000")
                )
            ],
        ),
        ctx,
    )
    ordered = await procurement_service.mark_ordered(po.id, ctx)
    grn = await procurement_service.create_goods_receipt(
        CreateGoodsReceiptInput(
            po_id=ordered.id,
            items=[
                GoodsReceiptItemInput(
                    po_item_id=ordered.items[0].id,
                    drug_id=drug_id,
                    quantity_received=Decimal("100"),
                    lot_no="LOT002",
                    expiry_date=_expiry(),
                    unit_cost=Decimal("4800"),
                )
            ],
        ),
        ctx,
    )
    confirmed = await procurement_service.confirm_goods_receipt(grn.id, ctx)
    fetched_grn = await procurement_service.get_goods_receipt(confirmed.id, ctx)
    assert fetched_grn.status == "CONFIRMED"

    updated_po = await procurement_service.get_purchase_order(ordered.id, ctx)
    assert updated_po.status == PurchaseOrderStatus.RECEIVED.value

    closed = await procurement_service.close_purchase_order(updated_po.id, ctx)
    assert closed.status == PurchaseOrderStatus.CLOSED.value

    assert len(events) == 1
    assert events[0].grn_id == confirmed.id
    assert events[0].items[0].drug_id == drug_id
    assert events[0].items[0].lot_no == "LOT002"
    assert events[0].items[0].quantity == Decimal("100")


async def test_confirm_over_receipt_rejected(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC I"), ctx)
    drug_id = uuid4()
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=drug_id, quantity_ordered=Decimal("10"), unit_price=Decimal("1000")
                )
            ],
        ),
        ctx,
    )
    ordered = await procurement_service.mark_ordered(po.id, ctx)
    grn = await procurement_service.create_goods_receipt(
        CreateGoodsReceiptInput(
            po_id=ordered.id,
            items=[
                GoodsReceiptItemInput(
                    po_item_id=ordered.items[0].id,
                    drug_id=drug_id,
                    quantity_received=Decimal("999"),
                    lot_no="LOT003",
                    expiry_date=_expiry(),
                    unit_cost=Decimal("100"),
                )
            ],
        ),
        ctx,
    )
    with pytest.raises(ValidationError):
        await procurement_service.confirm_goods_receipt(grn.id, ctx)


async def test_confirm_before_ordered_rejected(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC J"), ctx)
    drug_id = uuid4()
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=drug_id, quantity_ordered=Decimal("10"), unit_price=Decimal("1000")
                )
            ],
        ),
        ctx,
    )
    grn = await procurement_service.create_goods_receipt(
        CreateGoodsReceiptInput(
            po_id=po.id,
            items=[
                GoodsReceiptItemInput(
                    po_item_id=po.items[0].id,
                    drug_id=drug_id,
                    quantity_received=Decimal("5"),
                    lot_no="LOT004",
                    expiry_date=_expiry(),
                    unit_cost=Decimal("100"),
                )
            ],
        ),
        ctx,
    )
    with pytest.raises(ValidationError):
        await procurement_service.confirm_goods_receipt(grn.id, ctx)


async def test_create_goods_receipt_unknown_po_404(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await procurement_service.create_goods_receipt(
            CreateGoodsReceiptInput(po_id=uuid4(), items=[]), ctx
        )


async def test_create_goods_receipt_unknown_po_item_rejected_not_500(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    """A ``po_item_id`` not belonging to the PO must surface as 422, not a raw FK
    ``IntegrityError`` on insert — checked against the already-loaded PO's own
    items before the line is even built (see ``ProcurementService.create_goods_receipt``).
    """
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC L"), ctx)
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=uuid4(), quantity_ordered=Decimal("10"), unit_price=Decimal("1000")
                )
            ],
        ),
        ctx,
    )
    with pytest.raises(ValidationError):
        await procurement_service.create_goods_receipt(
            CreateGoodsReceiptInput(
                po_id=po.id,
                items=[
                    GoodsReceiptItemInput(
                        po_item_id=uuid4(),
                        drug_id=uuid4(),
                        quantity_received=Decimal("1"),
                        lot_no="LOT005",
                        expiry_date=_expiry(),
                        unit_cost=Decimal("1"),
                    )
                ],
            ),
            ctx,
        )


async def test_confirm_empty_receipt_rejected(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC K"), ctx)
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=uuid4(), quantity_ordered=Decimal("10"), unit_price=Decimal("1000")
                )
            ],
        ),
        ctx,
    )
    await procurement_service.mark_ordered(po.id, ctx)
    grn = await procurement_service.create_goods_receipt(
        CreateGoodsReceiptInput(po_id=po.id, items=[]), ctx
    )
    with pytest.raises(ValidationError):
        await procurement_service.confirm_goods_receipt(grn.id, ctx)


async def test_get_unknown_goods_receipt_404(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await procurement_service.get_goods_receipt(uuid4(), ctx)


# --- audit trail: cam kết tài chính với NCC + xác nhận nhận hàng thật --------


async def test_mark_ordered_and_confirm_receipt_each_leave_an_audit_row(
    procurement_service: ProcurementService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Does not trust the call sites to be wired — reads the table back."""
    supplier = await procurement_service.create_supplier(CreateSupplierInput(name="NCC Audit"), ctx)
    drug_id = uuid4()
    po = await procurement_service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier.id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=drug_id, quantity_ordered=Decimal("10"), unit_price=Decimal("1000")
                )
            ],
        ),
        ctx,
    )
    ordered = await procurement_service.mark_ordered(po.id, ctx)
    grn = await procurement_service.create_goods_receipt(
        CreateGoodsReceiptInput(
            po_id=ordered.id,
            items=[
                GoodsReceiptItemInput(
                    po_item_id=ordered.items[0].id,
                    drug_id=drug_id,
                    quantity_received=Decimal("10"),
                    lot_no="LOT-AUDIT",
                    expiry_date=_expiry(),
                    unit_cost=Decimal("900"),
                )
            ],
        ),
        ctx,
    )
    confirmed = await procurement_service.confirm_goods_receipt(grn.id, ctx)

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)

        po_entries = await repo.list(ctx.tenant_id, action=AuditAction.PROCUREMENT_PO_ORDERED)
        matching = [e for e in po_entries if e.target_id == str(ordered.id)]
        assert len(matching) == 1
        assert matching[0].actor_user_id == ctx.user_id

        grn_entries = await repo.list(ctx.tenant_id, action=AuditAction.PROCUREMENT_GRN_CONFIRMED)
        matching = [e for e in grn_entries if e.target_id == str(confirmed.id)]
        assert len(matching) == 1
