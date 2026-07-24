"""Bulk on-hand-per-drug read (``on_hand_by_drug``) — the port the analytics
reorder run reads to compare current stock against a computed reorder point
(PROJECT_STATE §7am). The point under test: summed per drug, positive-only, per branch.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.inventory.application import InventoryService, ReceiveStockInput


async def _receive(
    svc: InventoryService, ctx: RequestContext, drug_id: object, lot: str, qty: str
) -> None:
    await svc.receive_stock(
        ReceiveStockInput(
            drug_id=drug_id,  # type: ignore[arg-type]
            lot_no=lot,
            expiry_date=date(2027, 1, 1),
            quantity=Decimal(qty),
            cost_price=Decimal("1000"),
        ),
        ctx,
    )


async def test_on_hand_by_drug_sums_across_batches(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug_a, drug_b = uuid4(), uuid4()
    await _receive(inventory_service, ctx, drug_a, "L1", "100")
    await _receive(inventory_service, ctx, drug_a, "L2", "40")  # second batch, same drug
    await _receive(inventory_service, ctx, drug_b, "L3", "7")

    rows = await inventory_service.on_hand_by_drug(ctx)
    by_drug = {r.drug_id: r.on_hand for r in rows}
    assert by_drug[drug_a] == Decimal("140")  # 100 + 40
    assert by_drug[drug_b] == Decimal("7")
    assert all(r.branch_id == ctx.branch_id for r in rows)


async def test_on_hand_by_drug_matches_single_read(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    drug = uuid4()
    await _receive(inventory_service, ctx, drug, "L1", "55")

    bulk = {r.drug_id: r.on_hand for r in await inventory_service.on_hand_by_drug(ctx)}
    single = await inventory_service.on_hand(drug, ctx)
    assert bulk[drug] == single == Decimal("55")


async def test_on_hand_by_drug_empty_branch_is_empty(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    rows = await inventory_service.on_hand_by_drug(ctx, branch_id=uuid4())
    assert rows == []
