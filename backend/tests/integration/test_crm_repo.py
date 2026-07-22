from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from pharmacy_os.modules.catalog.domain import ActiveIngredient
from pharmacy_os.modules.catalog.infrastructure import SqlAlchemyActiveIngredientRepository
from pharmacy_os.modules.crm.application import (
    AddAllergyInput,
    AddConditionInput,
    CreateCustomerInput,
    CrmService,
)
from pharmacy_os.modules.crm.domain import AllergySeverity


async def _seed_ingredient(
    session_factory: async_sessionmaker[AsyncSession], name: str = "Penicillin"
) -> ActiveIngredient:
    async with session_factory() as session:
        repo = SqlAlchemyActiveIngredientRepository(session)
        ingredient = ActiveIngredient(name=name)
        await repo.add(ingredient)
        await session.commit()
    return ingredient


async def test_create_and_get_customer(crm_service: CrmService, ctx: RequestContext) -> None:
    created = await crm_service.create_customer(
        CreateCustomerInput(full_name="Nguyễn Văn A", phone="0900000000"), ctx
    )
    assert created.allergies == []

    fetched = await crm_service.get_customer(created.id, ctx)
    assert fetched.full_name == "Nguyễn Văn A"
    assert fetched.phone == "0900000000"


async def test_tenant_isolation(crm_service: CrmService, ctx: RequestContext) -> None:
    created = await crm_service.create_customer(CreateCustomerInput(full_name="X"), ctx)
    other = RequestContext(
        tenant_id=uuid4(),
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=ctx.permissions,
    )
    with pytest.raises(NotFoundError):
        await crm_service.get_customer(created.id, other)


async def test_permission_enforced(crm_service: CrmService, ctx: RequestContext) -> None:
    no_perm = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset(),
    )
    with pytest.raises(PermissionDeniedError):
        await crm_service.create_customer(CreateCustomerInput(full_name="Y"), no_perm)


async def test_get_unknown_customer_404(crm_service: CrmService, ctx: RequestContext) -> None:
    with pytest.raises(NotFoundError):
        await crm_service.get_customer(uuid4(), ctx)


async def test_add_allergy_round_trips(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _seed_ingredient(session_factory)
    created = await crm_service.create_customer(CreateCustomerInput(full_name="Z"), ctx)

    updated = await crm_service.add_allergy(
        created.id,
        AddAllergyInput(
            ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE, note="Sốc phản vệ"
        ),
        ctx,
    )
    assert len(updated.allergies) == 1
    assert updated.allergies[0].ingredient_id == ingredient.id
    assert updated.allergies[0].severity == "SEVERE"

    fetched = await crm_service.get_customer(created.id, ctx)
    assert len(fetched.allergies) == 1
    assert fetched.allergies[0].note == "Sốc phản vệ"


async def test_duplicate_allergy_rejected(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _seed_ingredient(session_factory)
    created = await crm_service.create_customer(CreateCustomerInput(full_name="W"), ctx)
    await crm_service.add_allergy(
        created.id, AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD), ctx
    )
    with pytest.raises(ValidationError):
        await crm_service.add_allergy(
            created.id,
            AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.SEVERE),
            ctx,
        )


async def test_add_allergy_unknown_customer_404(
    crm_service: CrmService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    ingredient = await _seed_ingredient(session_factory)
    with pytest.raises(NotFoundError):
        await crm_service.add_allergy(
            uuid4(),
            AddAllergyInput(ingredient_id=ingredient.id, severity=AllergySeverity.MILD),
            ctx,
        )


async def test_add_allergy_unknown_ingredient_404_not_500(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """FK violation (unknown ingredient_id) must surface as 404, not a raw
    IntegrityError/500 — see CrmService.add_allergy."""
    created = await crm_service.create_customer(CreateCustomerInput(full_name="T"), ctx)
    with pytest.raises(NotFoundError):
        await crm_service.add_allergy(
            created.id,
            AddAllergyInput(ingredient_id=uuid4(), severity=AllergySeverity.MILD),
            ctx,
        )


async def test_add_condition_round_trips_and_rejects_duplicate(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    created = await crm_service.create_customer(CreateCustomerInput(full_name="V"), ctx)
    updated = await crm_service.add_condition(
        created.id, AddConditionInput(condition_code="E11", note="Đái tháo đường type 2"), ctx
    )
    assert updated.conditions[0].condition_code == "E11"

    with pytest.raises(ValidationError):
        await crm_service.add_condition(created.id, AddConditionInput(condition_code="E11"), ctx)


async def test_list_customers_ordered_by_name(crm_service: CrmService, ctx: RequestContext) -> None:
    await crm_service.create_customer(CreateCustomerInput(full_name="Bình"), ctx)
    await crm_service.create_customer(CreateCustomerInput(full_name="An"), ctx)
    items = await crm_service.list_customers(ctx)
    assert [c.full_name for c in items] == ["An", "Bình"]


async def test_non_positive_weight_rejected(crm_service: CrmService, ctx: RequestContext) -> None:
    with pytest.raises(ValidationError):
        await crm_service.create_customer(
            CreateCustomerInput(full_name="U", weight_kg=Decimal("0")), ctx
        )
