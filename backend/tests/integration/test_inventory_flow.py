from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, SqlAlchemyAuditLogRepository
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pharmacy_os.core.events import DomainEvent, InMemoryEventBus
from pharmacy_os.modules.inventory.application import (
    DispenseInput,
    InventoryService,
    ReceiveStockInput,
)
from pharmacy_os.modules.inventory.domain import (
    StockMovedIn,
    StockMovedOut,
    StockReconciliationNeeded,
)
from pharmacy_os.modules.inventory.infrastructure import SqlAlchemyStockReconciliationRepository


async def test_receive_reflects_on_hand(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug_id = uuid4()
    receipt = await inventory_service.receive_stock(
        ReceiveStockInput(
            drug_id=drug_id,
            lot_no="L1",
            expiry_date=date(2027, 1, 1),
            quantity=Decimal("100"),
            cost_price=Decimal("1000"),
        ),
        ctx,
    )
    assert receipt.on_hand == Decimal("100")
    assert await inventory_service.on_hand(drug_id, ctx) == Decimal("100")


async def test_fefo_dispense_picks_nearest_expiry(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug_id = uuid4()
    # 🔴 Hai hạn dùng này từng ghi CỨNG `date(2027,1,1)` và `date(2026,8,1)`. Lô "NEAR" hết
    #    hạn ngày 2026-08-01, nên **từ 2026-08-02 test tự đỏ**: `dispense_stock` lọc lô hết
    #    hạn (`not_expired_on=date.today()`) ⇒ chỉ còn 10 đơn vị ⇒ xuất 12 trả 409.
    #    Sản phẩm ĐÚNG (không được xuất lô hết hạn); phép kiểm sai vì ghim ngày tuyệt đối.
    #    Nay tính tương đối như `_receive_with_expiry` cuối tệp này vẫn làm — cùng tệp đã có
    #    sẵn mẫu đúng, chỗ này chỉ là chỗ quên dùng nó.
    xa = date.today() + timedelta(days=365)
    gan = date.today() + timedelta(days=30)
    # Far-expiry batch received FIRST; near-expiry batch received SECOND.
    await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "FAR", xa, Decimal("10"), Decimal("1000")),
        ctx,
    )
    near = await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "NEAR", gan, Decimal("10"), Decimal("1000")),
        ctx,
    )

    result = await inventory_service.dispense_stock(
        DispenseInput(drug_id=drug_id, quantity=Decimal("12")), ctx
    )
    # FEFO: 10 from the near-expiry batch, then 2 from the far one.
    assert result.on_hand == Decimal("8")
    assert result.allocations[0].batch_id == near.batch_id
    assert result.allocations[0].quantity == Decimal("10")
    assert result.allocations[1].quantity == Decimal("2")


async def test_dispense_insufficient_raises_and_rolls_back(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug_id = uuid4()
    await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "L1", date(2027, 1, 1), Decimal("5"), Decimal("1000")), ctx
    )
    with pytest.raises(ConflictError):
        await inventory_service.dispense_stock(
            DispenseInput(drug_id=drug_id, quantity=Decimal("6")), ctx
        )
    # Rolled back: stock untouched.
    assert await inventory_service.on_hand(drug_id, ctx) == Decimal("5")


async def test_expired_batch_excluded_from_fefo(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug_id = uuid4()
    await inventory_service.receive_stock(
        ReceiveStockInput(
            drug_id, "OLD", date.today() - timedelta(days=1), Decimal("50"), Decimal("1000")
        ),
        ctx,
    )
    # Only an expired batch exists -> cannot dispense.
    with pytest.raises(ConflictError):
        await inventory_service.dispense_stock(
            DispenseInput(drug_id=drug_id, quantity=Decimal("1")), ctx
        )


async def test_near_expiry_listing(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug_id = uuid4()
    await inventory_service.receive_stock(
        ReceiveStockInput(
            drug_id, "SOON", date.today() + timedelta(days=30), Decimal("10"), Decimal("1000")
        ),
        ctx,
    )
    await inventory_service.receive_stock(
        ReceiveStockInput(
            drug_id, "LATER", date.today() + timedelta(days=400), Decimal("10"), Decimal("1000")
        ),
        ctx,
    )
    items = await inventory_service.list_near_expiry(ctx, within_days=90)
    assert [i.lot_no for i in items] == ["SOON"]


async def test_events_published_after_commit(
    inventory_service: InventoryService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    seen: list[str] = []

    async def record(event: DomainEvent) -> None:
        seen.append(event.name)

    event_bus.subscribe(StockMovedIn, record)
    event_bus.subscribe(StockMovedOut, record)

    drug_id = uuid4()
    await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "L1", date(2027, 1, 1), Decimal("10"), Decimal("1000")), ctx
    )
    await inventory_service.dispense_stock(
        DispenseInput(drug_id=drug_id, quantity=Decimal("3")), ctx
    )
    assert seen == ["StockMovedIn", "StockMovedOut"]


# --- audit trail: manual nhập/xuất kho qua API (không tính phản ứng cross-module) --


async def test_receive_and_dispense_each_leave_an_audit_row(
    inventory_service: InventoryService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Does not trust the call sites to be wired — reads the table back."""
    drug_id = uuid4()
    receipt = await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "L1", date(2027, 1, 1), Decimal("10"), Decimal("1000")), ctx
    )
    await inventory_service.dispense_stock(
        DispenseInput(drug_id=drug_id, quantity=Decimal("3")), ctx
    )

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)

        received = await repo.list(ctx.tenant_id, action=AuditAction.INVENTORY_STOCK_RECEIVED)
        matching = [e for e in received if e.target_id == str(receipt.batch_id)]
        assert len(matching) == 1
        assert matching[0].actor_user_id == ctx.user_id

        dispensed = await repo.list(ctx.tenant_id, action=AuditAction.INVENTORY_STOCK_DISPENSED)
        matching = [e for e in dispensed if e.target_id == str(drug_id)]
        assert len(matching) == 1


# --- reconciliation: tra cứu + xử lý ca va chạm lô/lỗi GRN --------------------


async def _seed_reconciliation(
    session_factory: async_sessionmaker[AsyncSession],
    ctx: RequestContext,
    *,
    resolved: bool = False,
) -> StockReconciliationNeeded:
    record = StockReconciliationNeeded(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        grn_id=uuid4(),
        reason="lot_collision: mẫu test",
        resolved=resolved,
    )
    async with session_factory() as session:
        repo = SqlAlchemyStockReconciliationRepository(session, ctx)
        await repo.add(record)
        await session.commit()
    return record


async def test_list_reconciliations_filters_by_resolved(
    inventory_service: InventoryService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    open_record = await _seed_reconciliation(session_factory, ctx, resolved=False)
    closed_record = await _seed_reconciliation(session_factory, ctx, resolved=True)

    everything = await inventory_service.list_reconciliations(ctx)
    assert {r.id for r in everything} == {open_record.id, closed_record.id}

    only_open = await inventory_service.list_reconciliations(ctx, resolved=False)
    assert [r.id for r in only_open] == [open_record.id]

    only_closed = await inventory_service.list_reconciliations(ctx, resolved=True)
    assert [r.id for r in only_closed] == [closed_record.id]


async def test_resolve_reconciliation_leaves_an_audit_row(
    inventory_service: InventoryService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Does not trust the call sites to be wired — reads the table back."""
    record = await _seed_reconciliation(session_factory, ctx)

    resolved = await inventory_service.resolve_reconciliation(record.id, ctx)
    assert resolved.resolved is True

    fetched = await inventory_service.list_reconciliations(ctx, resolved=True)
    assert [r.id for r in fetched] == [record.id]

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(
            ctx.tenant_id, action=AuditAction.INVENTORY_RECONCILIATION_RESOLVED
        )
        matching = [e for e in entries if e.target_id == str(record.id)]
        assert len(matching) == 1
        assert matching[0].actor_user_id == ctx.user_id


async def test_resolve_already_resolved_reconciliation_rejected(
    inventory_service: InventoryService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    record = await _seed_reconciliation(session_factory, ctx, resolved=True)
    with pytest.raises(ConflictError):
        await inventory_service.resolve_reconciliation(record.id, ctx)


async def test_resolve_unknown_reconciliation_raises(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await inventory_service.resolve_reconciliation(uuid4(), ctx)


# --- gộp lô (PA B): nhập lại cùng (drug, chi nhánh, lô) -----------------------


async def test_receive_same_lot_same_expiry_merges(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug_id = uuid4()
    await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "L1", date(2027, 1, 1), Decimal("10"), Decimal("1000")), ctx
    )
    receipt = await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "L1", date(2027, 1, 1), Decimal("10"), Decimal("1200")), ctx
    )

    # Same batch, not a second one — on-hand reflects both receipts.
    assert await inventory_service.on_hand(drug_id, ctx) == Decimal("20")
    first_receipt_batch_id = receipt.batch_id
    again = await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "L1", date(2027, 1, 1), Decimal("5"), Decimal("900")), ctx
    )
    assert again.batch_id == first_receipt_batch_id


async def test_receive_same_lot_different_expiry_rejected(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug_id = uuid4()
    await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "L1", date(2027, 1, 1), Decimal("10"), Decimal("1000")), ctx
    )
    with pytest.raises(ValidationError):
        await inventory_service.receive_stock(
            ReceiveStockInput(drug_id, "L1", date(2027, 6, 1), Decimal("5"), Decimal("1000")), ctx
        )
    # Rejected before any write: on-hand untouched.
    assert await inventory_service.on_hand(drug_id, ctx) == Decimal("10")


async def test_list_stock_pages_soonest_expiring_first(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    """Tồn theo lô, cận hạn lên trước, phân trang (Sprint 10, D3).

    Ba lô cố ý NHẬP theo thứ tự ngược với hạn dùng: nếu bản cài đặt trả theo thứ
    tự nhập (hoặc theo id) thì test đỏ. Đây là điểm phân biệt duy nhất giữa "có
    sắp xếp" và "tình cờ đúng thứ tự".
    """
    drug_id = uuid4()
    for lot, days in (("XA-XA", 300), ("GIUA", 120), ("GAN-NHAT", 20)):
        await inventory_service.receive_stock(
            ReceiveStockInput(
                drug_id=drug_id,
                lot_no=lot,
                expiry_date=date.today() + timedelta(days=days),
                quantity=Decimal("10"),
                cost_price=Decimal("1000"),
            ),
            ctx,
        )

    rows = await inventory_service.list_stock(ctx)
    page = await inventory_service.list_stock(ctx, limit=2)
    rest = await inventory_service.list_stock(ctx, limit=2, offset=2)

    assert [r.lot_no for r in rows] == ["GAN-NHAT", "GIUA", "XA-XA"]
    assert [r.lot_no for r in page] == ["GAN-NHAT", "GIUA"]
    assert [r.lot_no for r in rest] == ["XA-XA"]
    assert all(r.quantity == Decimal("10") for r in rows)


async def test_list_stock_hides_emptied_lots(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    """Lô đã xuất hết KHÔNG còn nằm trong danh sách tồn."""
    drug_id = uuid4()
    await inventory_service.receive_stock(
        ReceiveStockInput(
            drug_id=drug_id,
            lot_no="HET-SACH",
            expiry_date=date.today() + timedelta(days=90),
            quantity=Decimal("5"),
            cost_price=Decimal("1000"),
        ),
        ctx,
    )
    await inventory_service.dispense_stock(
        DispenseInput(drug_id=drug_id, quantity=Decimal("5")), ctx
    )

    assert await inventory_service.list_stock(ctx) == []


async def test_list_stock_requires_inventory_read(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    blind = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset({"inventory.receive"}),
    )
    with pytest.raises(PermissionDeniedError):
        await inventory_service.list_stock(blind)
