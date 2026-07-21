"""InventoryService.dispense_for_sale: the reaction driven by SaleCompleted."""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.events import DomainEvent, InMemoryEventBus
from pharmacy_os.modules.inventory.application import (
    InventoryService,
    ReceiveStockInput,
    SaleDispenseItem,
)
from pharmacy_os.modules.inventory.domain import StockShortfallDetected


async def _receive(
    service: InventoryService, ctx: RequestContext, drug_id: object, qty: str
) -> None:
    await service.receive_stock(
        ReceiveStockInput(
            drug_id=drug_id,  # type: ignore[arg-type]
            lot_no="L1",
            expiry_date=date(2027, 1, 1),
            quantity=Decimal(qty),
            cost_price=Decimal("1000"),
        ),
        ctx,
    )


async def test_dispense_for_sale_decrements_by_fefo(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug = uuid4()
    await _receive(inventory_service, ctx, drug, "20")
    await inventory_service.dispense_for_sale(
        [SaleDispenseItem(drug_id=drug, quantity=Decimal("12"))], uuid4(), ctx
    )
    assert await inventory_service.on_hand(drug, ctx) == Decimal("8")


async def test_dispense_for_sale_is_idempotent(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug = uuid4()
    await _receive(inventory_service, ctx, drug, "20")
    order = uuid4()
    items = [SaleDispenseItem(drug_id=drug, quantity=Decimal("12"))]

    await inventory_service.dispense_for_sale(items, order, ctx)
    await inventory_service.dispense_for_sale(items, order, ctx)  # replay same order

    assert await inventory_service.on_hand(drug, ctx) == Decimal("8")  # decremented once


async def test_oversell_dispenses_available_and_flags_shortfall(
    inventory_service: InventoryService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    shortfalls: list[StockShortfallDetected] = []

    async def record(event: DomainEvent) -> None:
        assert isinstance(event, StockShortfallDetected)
        shortfalls.append(event)

    event_bus.subscribe(StockShortfallDetected, record)

    drug = uuid4()
    await _receive(inventory_service, ctx, drug, "5")
    order = uuid4()
    await inventory_service.dispense_for_sale(
        [SaleDispenseItem(drug_id=drug, quantity=Decimal("10"))], order, ctx
    )

    assert await inventory_service.on_hand(drug, ctx) == Decimal("0")  # not negative
    assert len(shortfalls) == 1
    assert shortfalls[0].requested == Decimal("10")
    assert shortfalls[0].available == Decimal("5")
    assert shortfalls[0].ref_id == order


async def test_no_stock_dispenses_nothing_and_flags(
    inventory_service: InventoryService, ctx: RequestContext, event_bus: InMemoryEventBus
) -> None:
    shortfalls: list[StockShortfallDetected] = []

    async def record(event: DomainEvent) -> None:
        assert isinstance(event, StockShortfallDetected)
        shortfalls.append(event)

    event_bus.subscribe(StockShortfallDetected, record)

    drug = uuid4()  # never received
    await inventory_service.dispense_for_sale(
        [SaleDispenseItem(drug_id=drug, quantity=Decimal("3"))], uuid4(), ctx
    )

    assert await inventory_service.on_hand(drug, ctx) == Decimal("0")
    assert shortfalls[0].requested == Decimal("3")
    assert shortfalls[0].available == Decimal("0")
