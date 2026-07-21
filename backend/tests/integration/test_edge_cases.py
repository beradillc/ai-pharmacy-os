"""Boundary/edge-case coverage for catalog & inventory use-cases.

Covers the cases called out for the self-refine pass: zero stock, zero
quantities, empty batch lists and duplicate drug identifiers.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ConflictError, ValidationError
from pharmacy_os.modules.catalog.application import CatalogService, CreateDrugInput
from pharmacy_os.modules.catalog.domain import RxClass
from pharmacy_os.modules.inventory.application import (
    DispenseInput,
    InventoryService,
    ReceiveStockInput,
)

# --- inventory boundaries --------------------------------------------------- #


async def test_on_hand_unknown_drug_is_zero(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    assert await inventory_service.on_hand(uuid4(), ctx) == Decimal("0")


async def test_receive_zero_quantity_rejected(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    with pytest.raises(ValidationError):
        await inventory_service.receive_stock(
            ReceiveStockInput(uuid4(), "L", date(2027, 1, 1), Decimal("0"), Decimal("0")),
            ctx,
        )


async def test_dispense_zero_quantity_rejected(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    with pytest.raises(ValidationError):
        await inventory_service.dispense_stock(
            DispenseInput(drug_id=uuid4(), quantity=Decimal("0")), ctx
        )


async def test_dispense_with_no_batches_conflicts(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    # Drug exists conceptually but has never been received -> empty batch list.
    with pytest.raises(ConflictError):
        await inventory_service.dispense_stock(
            DispenseInput(drug_id=uuid4(), quantity=Decimal("1")), ctx
        )


async def test_near_expiry_empty_when_nothing_received(
    inventory_service: InventoryService, ctx: RequestContext
) -> None:
    assert await inventory_service.list_near_expiry(ctx, within_days=30) == []


# --- catalog boundaries ----------------------------------------------------- #


async def test_list_drugs_empty(catalog_service: CatalogService, ctx: RequestContext) -> None:
    assert await catalog_service.list_drugs(ctx) == []


async def test_duplicate_barcode_across_same_tenant_rejected(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    payload = CreateDrugInput(
        name="Vitamin C", rx_class=RxClass.OTC, base_unit="viên", barcode="DUP-1"
    )
    await catalog_service.create_drug(payload, ctx)
    with pytest.raises(ConflictError):
        await catalog_service.create_drug(payload, ctx)


async def test_same_barcode_allowed_for_different_tenant(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    # Barcode uniqueness is scoped per tenant, not global.
    await catalog_service.create_drug(
        CreateDrugInput(name="A", rx_class=RxClass.OTC, base_unit="viên", barcode="SHARED"),
        ctx,
    )
    other = RequestContext(
        tenant_id=uuid4(),
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=ctx.permissions,
    )
    created = await catalog_service.create_drug(
        CreateDrugInput(name="B", rx_class=RxClass.OTC, base_unit="viên", barcode="SHARED"),
        other,
    )
    assert created.barcode == "SHARED"
