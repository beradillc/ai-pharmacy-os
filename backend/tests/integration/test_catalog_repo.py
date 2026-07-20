from decimal import Decimal

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from pharmacy_os.modules.catalog.application import (
    CatalogService,
    CreateDrugInput,
    DrugUnitInput,
)
from pharmacy_os.modules.catalog.domain import RxClass


async def test_create_and_get_drug(catalog_service: CatalogService, ctx: RequestContext) -> None:
    created = await catalog_service.create_drug(
        CreateDrugInput(
            name="Paracetamol 500mg",
            rx_class=RxClass.OTC,
            base_unit="viên",
            barcode="8935001",
            units=[DrugUnitInput(unit_name="vỉ", factor=Decimal("10"))],
        ),
        ctx,
    )
    assert created.units[0].unit_name == "vỉ"

    fetched = await catalog_service.get_drug(created.id, ctx)
    assert fetched.name == "Paracetamol 500mg"
    assert fetched.units[0].factor == Decimal("10")


async def test_duplicate_barcode_conflict(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    data = CreateDrugInput(name="A", rx_class=RxClass.OTC, base_unit="viên", barcode="123")
    await catalog_service.create_drug(data, ctx)
    with pytest.raises(ConflictError):
        await catalog_service.create_drug(data, ctx)


async def test_tenant_isolation(catalog_service: CatalogService, ctx: RequestContext) -> None:
    created = await catalog_service.create_drug(
        CreateDrugInput(name="X", rx_class=RxClass.OTC, base_unit="viên"), ctx
    )
    other = RequestContext(
        tenant_id=__import__("uuid").uuid4(),
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=ctx.permissions,
    )
    with pytest.raises(NotFoundError):
        await catalog_service.get_drug(created.id, other)


async def test_permission_enforced(catalog_service: CatalogService, ctx: RequestContext) -> None:
    no_perm = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset(),
    )
    with pytest.raises(PermissionDeniedError):
        await catalog_service.create_drug(
            CreateDrugInput(name="Y", rx_class=RxClass.OTC, base_unit="viên"), no_perm
        )
