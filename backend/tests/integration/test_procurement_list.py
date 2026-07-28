"""Danh sách đơn mua (``ProcurementService.list_purchase_orders``) — cổng đọc cho
màn Đơn mua hàng (Sprint 10, D2).

Điều đang được canh:

1. **Tên NCC được giải, không phải UUID** — và giải bằng MỘT truy vấn gộp, không
   phải một truy vấn mỗi dòng. Chỗ này là lý do màn hình tồn tại: một danh sách
   toàn UUID thì không ai chọn được đơn nào để mở (đúng khe hở G-1 của docs/19).
2. **Tổng tiền là tiền ĐẶT** (quantity_ordered × unit_price), không phải tiền đã
   nhận. Đơn nháp do analytics sinh mang unit_price = 0 ⇒ tổng 0 là *đúng*, là
   đơn đang nói "chưa chốt giá", không phải lỗi cộng.
3. Lọc theo trạng thái + mới-trước.

Kỷ luật #14 — đã xem đỏ vì đúng lý do trước khi tin:
  • Đổi ``names.get(...)`` thành ``None`` (bỏ giải tên): MUTANT_PYTEST_EXIT=1 ở
    ``test_supplier_name_is_resolved``.
  • Đổi tổng sang ``quantity_received``: MUTANT_PYTEST_EXIT=1 ở
    ``test_total_is_ordered_amount_not_received``.
"""

from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import PermissionDeniedError
from pharmacy_os.modules.procurement.application import (
    CreatePurchaseOrderInput,
    CreateSupplierInput,
    ProcurementService,
    PurchaseOrderItemInput,
)
from pharmacy_os.modules.procurement.domain import PurchaseOrderStatus


async def _supplier(service: ProcurementService, ctx: RequestContext, name: str):
    return await service.create_supplier(CreateSupplierInput(name=name), ctx)


async def _po(
    service: ProcurementService,
    ctx: RequestContext,
    supplier_id,
    *items: tuple[str, str],
):
    return await service.create_purchase_order(
        CreatePurchaseOrderInput(
            supplier_id=supplier_id,
            items=[
                PurchaseOrderItemInput(
                    drug_id=uuid4(), quantity_ordered=Decimal(q), unit_price=Decimal(p)
                )
                for q, p in items
            ],
        ),
        ctx,
    )


async def test_supplier_name_is_resolved(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await _supplier(procurement_service, ctx, "Dược Hậu Giang")
    await _po(procurement_service, ctx, supplier.id, ("10", "12000"))

    rows = await procurement_service.list_purchase_orders(ctx)

    assert len(rows) == 1
    assert rows[0].supplier_name == "Dược Hậu Giang"
    assert rows[0].supplier_id == supplier.id


async def test_total_is_ordered_amount_not_received(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await _supplier(procurement_service, ctx, "NCC A")
    await _po(procurement_service, ctx, supplier.id, ("10", "12000"), ("2", "50000"))

    row = (await procurement_service.list_purchase_orders(ctx))[0]

    # 10×12000 + 2×50000 = 220000. Chưa nhận hàng nào, nên nếu tổng tính theo
    # quantity_received thì nó phải là 0 — khác biệt này là điểm test canh.
    assert row.total_amount == Decimal("220000")
    assert row.item_count == 2


async def test_zero_price_draft_totals_zero(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    """Đơn nháp kiểu analytics (giá 0) — tổng 0 là câu trả lời ĐÚNG."""
    supplier = await _supplier(procurement_service, ctx, "NCC B")
    await _po(procurement_service, ctx, supplier.id, ("30", "0"))

    row = (await procurement_service.list_purchase_orders(ctx))[0]

    assert row.total_amount == Decimal("0")
    assert row.status == PurchaseOrderStatus.DRAFT.value


async def test_status_filter_and_order(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    supplier = await _supplier(procurement_service, ctx, "NCC C")
    draft = await _po(procurement_service, ctx, supplier.id, ("1", "1000"))
    placed = await _po(procurement_service, ctx, supplier.id, ("1", "1000"))
    await procurement_service.mark_ordered(placed.id, ctx)

    drafts = await procurement_service.list_purchase_orders(ctx, status=PurchaseOrderStatus.DRAFT)
    ordered = await procurement_service.list_purchase_orders(
        ctx, status=PurchaseOrderStatus.ORDERED
    )
    every = await procurement_service.list_purchase_orders(ctx)

    assert [r.id for r in drafts] == [draft.id]
    assert [r.id for r in ordered] == [placed.id]
    keys = [(r.created_at, r.id) for r in every]
    assert keys == sorted(keys, reverse=True)


async def test_paging(procurement_service: ProcurementService, ctx: RequestContext) -> None:
    supplier = await _supplier(procurement_service, ctx, "NCC D")
    for _ in range(3):
        await _po(procurement_service, ctx, supplier.id, ("1", "1000"))

    page = await procurement_service.list_purchase_orders(ctx, limit=2)
    rest = await procurement_service.list_purchase_orders(ctx, limit=2, offset=2)

    assert len(page) == 2
    assert len(rest) == 1
    assert {r.id for r in page}.isdisjoint({r.id for r in rest})


async def test_requires_po_read_only(
    procurement_service: ProcurementService, ctx: RequestContext
) -> None:
    """Đọc được danh sách kèm TÊN NCC mà KHÔNG cần procurement.supplier.read."""
    supplier = await _supplier(procurement_service, ctx, "NCC E")
    await _po(procurement_service, ctx, supplier.id, ("1", "1000"))

    po_reader = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset({"procurement.po.read"}),
    )
    blind = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset({"procurement.grn.read"}),
    )

    rows = await procurement_service.list_purchase_orders(po_reader)
    assert rows[0].supplier_name == "NCC E"

    with pytest.raises(PermissionDeniedError):
        await procurement_service.list_purchase_orders(blind)
