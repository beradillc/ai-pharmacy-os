"""InventoryService.receive_from_goods_receipt: the reaction driven by GoodsReceived."""

from datetime import date
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.events import DomainEvent, InMemoryEventBus
from pharmacy_os.modules.inventory.application import (
    GoodsReceiptLine,
    InventoryService,
    ReceiveStockInput,
)
from pharmacy_os.modules.inventory.domain import StockMovedIn
from pharmacy_os.modules.inventory.infrastructure import StockReconciliationNeededORM

_EXPIRY = date(2027, 1, 1)


def _line(drug_id: UUID, *, lot: str, qty: str, po_item_id: UUID | None = None) -> GoodsReceiptLine:
    return GoodsReceiptLine(
        drug_id=drug_id,
        lot_no=lot,
        expiry_date=_EXPIRY,
        unit_cost=Decimal("1000"),
        quantity=Decimal(qty),
        po_item_id=po_item_id,
    )


async def _reconciliations(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[StockReconciliationNeededORM]:
    async with session_factory() as session:
        rows = (await session.execute(select(StockReconciliationNeededORM))).scalars().all()
        return list(rows)


async def test_creates_one_batch_per_line(
    inventory_service: InventoryService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    moved_in: list[StockMovedIn] = []

    async def record(event: DomainEvent) -> None:
        assert isinstance(event, StockMovedIn)
        moved_in.append(event)

    event_bus.subscribe(StockMovedIn, record)

    drug_a, drug_b = uuid4(), uuid4()
    grn = uuid4()
    await inventory_service.receive_from_goods_receipt(
        [_line(drug_a, lot="LA", qty="30"), _line(drug_b, lot="LB", qty="12")], grn, ctx
    )

    assert await inventory_service.on_hand(drug_a, ctx) == Decimal("30")
    assert await inventory_service.on_hand(drug_b, ctx) == Decimal("12")
    assert len(moved_in) == 2


async def test_idempotent_on_grn_id(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug = uuid4()
    grn = uuid4()
    lines = [_line(drug, lot="L1", qty="20")]

    await inventory_service.receive_from_goods_receipt(lines, grn, ctx)
    await inventory_service.receive_from_goods_receipt(lines, grn, ctx)  # replay same GRN

    assert await inventory_service.on_hand(drug, ctx) == Decimal("20")  # created once


async def test_lot_collision_skips_line_and_flags_reconciliation(
    inventory_service: InventoryService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    drug = uuid4()
    # A batch for (drug, branch, lot "L1") already exists (manual receive).
    await inventory_service.receive_stock(
        ReceiveStockInput(
            drug_id=drug,
            lot_no="L1",
            expiry_date=_EXPIRY,
            quantity=Decimal("10"),
            cost_price=Decimal("900"),
        ),
        ctx,
    )

    colliding_po_item = uuid4()
    await inventory_service.receive_from_goods_receipt(
        [
            _line(drug, lot="L1", qty="5", po_item_id=colliding_po_item),  # collides -> skipped
            _line(drug, lot="L2", qty="7"),  # new lot -> created
        ],
        uuid4(),
        ctx,
    )

    # Only the non-colliding line landed: 10 (pre) + 7 (L2), NOT + 5.
    assert await inventory_service.on_hand(drug, ctx) == Decimal("17")

    recs = await _reconciliations(session_factory)
    assert len(recs) == 1
    assert recs[0].po_item_id == colliding_po_item
    assert recs[0].resolved is False
    assert "lot_collision" in recs[0].reason


async def test_zero_quantity_line_is_skipped(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug = uuid4()
    await inventory_service.receive_from_goods_receipt(
        [_line(drug, lot="L0", qty="0")], uuid4(), ctx
    )
    assert await inventory_service.on_hand(drug, ctx) == Decimal("0")
