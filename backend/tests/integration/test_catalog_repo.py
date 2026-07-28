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


async def test_get_drug_ingredients_resolves_id_and_name(
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

    refs = await catalog_service.get_drug_ingredients(created.id, ctx)
    assert {(r.ingredient_id, r.name) for r in refs} == {
        (amoxicillin.id, "Amoxicillin"),
        (clavulanic_acid.id, "Acid clavulanic"),
    }


async def test_get_drug_ingredients_empty_for_drug_without_ingredients(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    created = await catalog_service.create_drug(
        CreateDrugInput(name="Nước muối sinh lý", rx_class=RxClass.OTC, base_unit="chai"), ctx
    )
    assert await catalog_service.get_drug_ingredients(created.id, ctx) == []


async def test_get_drug_ingredients_unknown_drug_not_found(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await catalog_service.get_drug_ingredients(uuid4(), ctx)


async def test_get_drug_ingredients_permission_enforced(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    created = await catalog_service.create_drug(
        CreateDrugInput(name="V", rx_class=RxClass.OTC, base_unit="viên"), ctx
    )
    no_perm = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset(),
    )
    with pytest.raises(PermissionDeniedError):
        await catalog_service.get_drug_ingredients(created.id, no_perm)


async def test_get_drug_ingredients_tenant_isolation(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    created = await catalog_service.create_drug(
        CreateDrugInput(name="Iso", rx_class=RxClass.OTC, base_unit="viên"), ctx
    )
    other = RequestContext(
        tenant_id=uuid4(),
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=ctx.permissions,
    )
    with pytest.raises(NotFoundError):
        await catalog_service.get_drug_ingredients(created.id, other)


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


# --- audit trail: ai đã thêm/phân loại thuốc này vào catalog -------------------


async def test_create_drug_leaves_an_audit_row(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Does not trust the call sites to be wired — reads the table back."""
    created = await catalog_service.create_drug(
        CreateDrugInput(name="Aspirin 81mg", rx_class=RxClass.OTC, base_unit="viên"), ctx
    )

    async with session_factory() as session:
        repo = SqlAlchemyAuditLogRepository(session)
        entries = await repo.list(ctx.tenant_id, action=AuditAction.CATALOG_DRUG_CREATED)
        matching = [e for e in entries if e.target_id == str(created.id)]
        assert len(matching) == 1
        assert matching[0].actor_user_id == ctx.user_id


# --- tra tên hàng loạt: nền cho khe hở G-1 (docs/19) --------------------------


async def test_drug_names_resolves_many_in_one_call(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    a = await catalog_service.create_drug(
        CreateDrugInput(name="Amoxicillin 500mg", rx_class=RxClass.ETC, base_unit="viên"), ctx
    )
    b = await catalog_service.create_drug(
        CreateDrugInput(name="Omeprazole 20mg", rx_class=RxClass.ETC, base_unit="viên"), ctx
    )

    names = await catalog_service.drug_names([a.id, b.id], ctx)

    assert names == {a.id: "Amoxicillin 500mg", b.id: "Omeprazole 20mg"}


async def test_drug_names_omits_unknown_id_instead_of_raising(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """A drug removed after a report was computed must not fail the whole screen."""
    known = await catalog_service.create_drug(
        CreateDrugInput(name="Vitamin C 1000mg", rx_class=RxClass.OTC, base_unit="viên"), ctx
    )
    ghost = uuid4()

    names = await catalog_service.drug_names([known.id, ghost], ctx)

    assert names == {known.id: "Vitamin C 1000mg"}
    assert ghost not in names


async def test_drug_names_empty_input_does_not_hit_the_database(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    assert await catalog_service.drug_names([], ctx) == {}


async def test_drug_names_is_tenant_scoped(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Another tenant's id resolves to nothing — not to that tenant's drug name."""
    mine = await catalog_service.create_drug(
        CreateDrugInput(name="Cetirizine 10mg", rx_class=RxClass.OTC, base_unit="viên"), ctx
    )
    other = RequestContext(
        tenant_id=uuid4(),
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=ctx.permissions,
    )

    assert await catalog_service.drug_names([mine.id], other) == {}


async def test_drug_names_requires_catalog_read(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    unprivileged = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset(),
    )
    with pytest.raises(PermissionDeniedError):
        await catalog_service.drug_names([uuid4()], unprivileged)


async def _drug(
    service: CatalogService, ctx: RequestContext, name: str, barcode: str | None = None
):
    return await service.create_drug(
        CreateDrugInput(name=name, rx_class=RxClass.OTC, base_unit="viên", barcode=barcode),
        ctx,
    )


async def test_search_matches_name_case_insensitively(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Gõ "para" phải ra "Paracetamol" — chữ hoa/thường không được cản (Sprint 10, D3).

    Khẳng định này là lý do dùng ``ilike`` chứ không ``like``: trên SQLite ``like``
    vô tình không phân biệt hoa thường với ASCII, nên một test chỉ gõ đúng hoa
    thường sẽ xanh trên cả bản cài đặt sai. Test này gõ CHỮ THƯỜNG cho một tên
    VIẾT HOA đầu, đúng chỗ hai bản khác nhau trên Postgres.
    """
    await _drug(catalog_service, ctx, "Paracetamol 500mg")
    await _drug(catalog_service, ctx, "Amoxicillin 500mg")

    found = await catalog_service.list_drugs(ctx, search="para")

    assert [d.name for d in found] == ["Paracetamol 500mg"]


async def test_search_matches_exact_barcode(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    await _drug(catalog_service, ctx, "Vitamin C 500mg", barcode="8935001234567")
    await _drug(catalog_service, ctx, "Vitamin B1", barcode="8935009999999")

    found = await catalog_service.list_drugs(ctx, search="8935001234567")

    assert [d.name for d in found] == ["Vitamin C 500mg"]


async def test_ids_filter_labels_a_page_in_one_call(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    a = await _drug(catalog_service, ctx, "Aspirin 81mg")
    b = await _drug(catalog_service, ctx, "Berberin")
    await _drug(catalog_service, ctx, "Cetirizin 10mg")

    found = await catalog_service.list_drugs(ctx, ids=[a.id, b.id])

    assert {d.id for d in found} == {a.id, b.id}


async def test_empty_ids_is_not_the_same_as_no_filter(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """``ids=[]`` = "không hỏi id nào" ⇒ rỗng; ``ids=None`` = "không lọc" ⇒ đủ."""
    await _drug(catalog_service, ctx, "Domperidon 10mg")

    assert await catalog_service.list_drugs(ctx, ids=[]) == []
    assert len(await catalog_service.list_drugs(ctx, ids=None)) == 1
