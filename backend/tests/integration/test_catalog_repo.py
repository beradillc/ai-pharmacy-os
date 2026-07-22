from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from pharmacy_os.modules.catalog.application import (
    CatalogService,
    CreateDrugInput,
    DrugIngredientInput,
    DrugUnitInput,
)
from pharmacy_os.modules.catalog.domain import ActiveIngredient, RxClass
from pharmacy_os.modules.catalog.infrastructure import SqlAlchemyActiveIngredientRepository


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


async def test_create_drug_with_existing_ingredients_round_trips(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = SqlAlchemyActiveIngredientRepository(session)
        amoxicillin = ActiveIngredient(name="Amoxicillin")
        clavulanic_acid = ActiveIngredient(name="Acid clavulanic")
        await repo.add(amoxicillin)
        await repo.add(clavulanic_acid)
        await session.commit()

    created = await catalog_service.create_drug(
        CreateDrugInput(
            name="Augmentin 625mg",
            rx_class=RxClass.ETC,
            base_unit="viên",
            ingredients=[
                DrugIngredientInput(ingredient_id=amoxicillin.id, amount=Decimal("500"), unit="mg"),
                DrugIngredientInput(
                    ingredient_id=clavulanic_acid.id, amount=Decimal("125"), unit="mg"
                ),
            ],
        ),
        ctx,
    )
    assert {i.ingredient_id for i in created.ingredients} == {
        amoxicillin.id,
        clavulanic_acid.id,
    }

    fetched = await catalog_service.get_drug(created.id, ctx)
    assert {(i.ingredient_id, i.amount, i.unit) for i in fetched.ingredients} == {
        (amoxicillin.id, Decimal("500"), "mg"),
        (clavulanic_acid.id, Decimal("125"), "mg"),
    }


async def test_create_drug_unknown_ingredient_not_found(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await catalog_service.create_drug(
            CreateDrugInput(
                name="Z",
                rx_class=RxClass.OTC,
                base_unit="viên",
                ingredients=[
                    DrugIngredientInput(ingredient_id=uuid4(), amount=Decimal("1"), unit="mg")
                ],
            ),
            ctx,
        )


async def test_create_drug_duplicate_ingredient_rejected(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = SqlAlchemyActiveIngredientRepository(session)
        ingredient = ActiveIngredient(name="Paracetamol")
        await repo.add(ingredient)
        await session.commit()

    with pytest.raises(ValidationError):
        await catalog_service.create_drug(
            CreateDrugInput(
                name="W",
                rx_class=RxClass.OTC,
                base_unit="viên",
                ingredients=[
                    DrugIngredientInput(
                        ingredient_id=ingredient.id, amount=Decimal("500"), unit="mg"
                    ),
                    DrugIngredientInput(
                        ingredient_id=ingredient.id, amount=Decimal("250"), unit="mg"
                    ),
                ],
            ),
            ctx,
        )


async def test_active_ingredient_repository_find_by_name_and_list(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        repo = SqlAlchemyActiveIngredientRepository(session)
        await repo.add(ActiveIngredient(name="Ibuprofen", name_en="Ibuprofen"))
        await session.commit()

    async with session_factory() as session:
        repo = SqlAlchemyActiveIngredientRepository(session)
        found = await repo.find_by_name("Ibuprofen")
        assert found is not None
        assert found.name_en == "Ibuprofen"
        assert await repo.find_by_name("Unknown") is None
        assert len(await repo.list()) == 1
