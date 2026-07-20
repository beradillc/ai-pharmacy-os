from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ConflictError
from pharmacy_os.core.events import DomainEvent, InMemoryEventBus
from pharmacy_os.modules.inventory.application import (
    DispenseInput,
    InventoryService,
    ReceiveStockInput,
)
from pharmacy_os.modules.inventory.domain import StockMovedIn, StockMovedOut


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
    # Far-expiry batch received FIRST; near-expiry batch received SECOND.
    await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "FAR", date(2027, 1, 1), Decimal("10"), Decimal("1000")),
        ctx,
    )
    near = await inventory_service.receive_stock(
        ReceiveStockInput(drug_id, "NEAR", date(2026, 8, 1), Decimal("10"), Decimal("1000")),
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
