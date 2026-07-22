"""S6 5.5.4 cross-module: auto-check drug interactions on sale / dispense.

Warn-only reaction declared at the composition root (``wire_interaction_safety_check``),
same pattern as ``wire_sale_dispensing``. Sales/prescription never import clinical or
catalog — the handler in the ``api`` layer resolves the basket's ingredients (catalog,
S6 Bước 1) and drives the tenant-gated clinical check, which audits an
``AiRecommendation``. Both trigger events are post-commit, so this only warns.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.api.v1.cross_module import wire_interaction_safety_check
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus, InMemoryEventBus
from pharmacy_os.modules.catalog.application import (
    CatalogService,
    CreateDrugInput,
    DrugIngredientInput,
)
from pharmacy_os.modules.catalog.domain import ActiveIngredient, RxClass
from pharmacy_os.modules.catalog.infrastructure import SqlAlchemyActiveIngredientRepository
from pharmacy_os.modules.clinical.application import ClinicalService, SetTenantAiSettingsInput
from pharmacy_os.modules.clinical.domain import (
    AiContextType,
    DrugInteraction,
    InteractionSeverity,
)
from pharmacy_os.modules.clinical.infrastructure import (
    AiRecommendationORM,
    SqlAlchemyDrugInteractionRepository,
)
from pharmacy_os.modules.prescription.application import (
    CreatePrescriptionInput,
    PrescriptionItemInput,
    PrescriptionService,
)
from pharmacy_os.modules.prescription.domain import PrescriptionDispensed
from pharmacy_os.modules.sales.domain import SaleCompleted, SoldItem


@pytest.fixture
def wired_container(
    event_bus: InMemoryEventBus,
    catalog_service: CatalogService,
    clinical_service: ClinicalService,
    prescription_service: PrescriptionService,
) -> Container:
    """A container with the real services + the S6 5.5.4 subscription wired."""
    container = Container()
    container.register_instance(EventBus, event_bus)  # type: ignore[type-abstract]
    container.register_instance(CatalogService, catalog_service)
    container.register_instance(ClinicalService, clinical_service)
    container.register_instance(PrescriptionService, prescription_service)
    wire_interaction_safety_check(container)
    return container


async def _seed_interaction(
    session_factory: async_sessionmaker[AsyncSession],
    a: str,
    b: str,
    severity: InteractionSeverity,
) -> None:
    async with session_factory() as session:
        repo = SqlAlchemyDrugInteractionRepository(session)
        await repo.add(
            DrugInteraction(
                ingredient_a=a,
                ingredient_b=b,
                severity=severity,
                mechanism="cơ chế mẫu",
                management="xử trí mẫu",
                source="test",
            )
        )
        await session.commit()


async def _new_ingredient(
    session_factory: async_sessionmaker[AsyncSession], name: str
) -> ActiveIngredient:
    async with session_factory() as session:
        repo = SqlAlchemyActiveIngredientRepository(session)
        ingredient = ActiveIngredient(name=name)
        await repo.add(ingredient)
        await session.commit()
    return ingredient


async def _new_drug(
    catalog_service: CatalogService, ctx: RequestContext, name: str, ingredient_ids: list[UUID]
) -> UUID:
    created = await catalog_service.create_drug(
        CreateDrugInput(
            name=name,
            rx_class=RxClass.OTC,
            base_unit="viên",
            ingredients=[
                DrugIngredientInput(ingredient_id=iid, amount=Decimal("1"), unit="mg")
                for iid in ingredient_ids
            ],
        ),
        ctx,
    )
    return created.id


async def _enable_ai(clinical_service: ClinicalService, ctx: RequestContext) -> None:
    await clinical_service.set_tenant_ai_settings(
        SetTenantAiSettingsInput(enable_clinical_ai=True), ctx
    )


async def _recommendations_for(
    session_factory: async_sessionmaker[AsyncSession], tenant_id: UUID, context_id: UUID
) -> list[AiRecommendationORM]:
    async with session_factory() as session:
        result = await session.execute(
            select(AiRecommendationORM).where(
                AiRecommendationORM.tenant_id == tenant_id,
                AiRecommendationORM.context_id == context_id,
            )
        )
        return list(result.scalars().all())


async def _count_recommendations(
    session_factory: async_sessionmaker[AsyncSession], tenant_id: UUID
) -> int:
    async with session_factory() as session:
        result = await session.execute(
            select(func.count())
            .select_from(AiRecommendationORM)
            .where(AiRecommendationORM.tenant_id == tenant_id)
        )
        return int(result.scalar_one())


def _sale(ctx: RequestContext, order_id: UUID, drug_ids: list[UUID]) -> SaleCompleted:
    return SaleCompleted(
        tenant_id=ctx.tenant_id,
        order_id=order_id,
        branch_id=ctx.branch_id,
        client_uuid=str(order_id),
        items=tuple(SoldItem(drug_id=d, quantity=Decimal("1")) for d in drug_ids),
    )


async def test_sale_with_interacting_drugs_audits_a_flagged_recommendation(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    catalog_service: CatalogService,
    clinical_service: ClinicalService,
    ctx: RequestContext,
) -> None:
    await _enable_ai(clinical_service, ctx)
    await _seed_interaction(session_factory, "Warfarin", "Aspirin", InteractionSeverity.MAJOR)
    warfarin = await _new_ingredient(session_factory, "Warfarin")
    aspirin = await _new_ingredient(session_factory, "Aspirin")
    drug_a = await _new_drug(catalog_service, ctx, "Thuốc W", [warfarin.id])
    drug_b = await _new_drug(catalog_service, ctx, "Thuốc A", [aspirin.id])

    order_id = uuid4()
    await event_bus.publish(_sale(ctx, order_id, [drug_a, drug_b]))

    recs = await _recommendations_for(session_factory, ctx.tenant_id, order_id)
    assert len(recs) == 1
    assert recs[0].context_type == AiContextType.SALE.value
    assert recs[0].requires_review is True  # a MAJOR finding forces pharmacist review


async def test_disabled_tenant_produces_no_recommendation_and_no_error(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    catalog_service: CatalogService,
    ctx: RequestContext,
) -> None:
    # AI intentionally NOT enabled for this tenant (default OFF).
    await _seed_interaction(session_factory, "Warfarin", "Aspirin", InteractionSeverity.MAJOR)
    warfarin = await _new_ingredient(session_factory, "Warfarin")
    aspirin = await _new_ingredient(session_factory, "Aspirin")
    drug_a = await _new_drug(catalog_service, ctx, "Thuốc W", [warfarin.id])
    drug_b = await _new_drug(catalog_service, ctx, "Thuốc A", [aspirin.id])

    order_id = uuid4()
    await event_bus.publish(_sale(ctx, order_id, [drug_a, drug_b]))  # must not raise

    assert await _count_recommendations(session_factory, ctx.tenant_id) == 0


async def test_single_ingredient_basket_is_skipped(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    catalog_service: CatalogService,
    clinical_service: ClinicalService,
    ctx: RequestContext,
) -> None:
    await _enable_ai(clinical_service, ctx)
    paracetamol = await _new_ingredient(session_factory, "Paracetamol")
    drug = await _new_drug(catalog_service, ctx, "Hạ sốt", [paracetamol.id])

    order_id = uuid4()
    await event_bus.publish(_sale(ctx, order_id, [drug]))

    # Fewer than two distinct ingredients → no interaction possible → skipped, no audit noise.
    assert await _count_recommendations(session_factory, ctx.tenant_id) == 0


async def test_no_known_interaction_still_audits_the_check(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    catalog_service: CatalogService,
    clinical_service: ClinicalService,
    ctx: RequestContext,
) -> None:
    await _enable_ai(clinical_service, ctx)  # no interactions seeded
    a = await _new_ingredient(session_factory, "Vitamin C")
    b = await _new_ingredient(session_factory, "Vitamin D")
    drug_a = await _new_drug(catalog_service, ctx, "VitC", [a.id])
    drug_b = await _new_drug(catalog_service, ctx, "VitD", [b.id])

    order_id = uuid4()
    await event_bus.publish(_sale(ctx, order_id, [drug_a, drug_b]))

    # Two ingredients but no known pair: the check still runs and is audited.
    recs = await _recommendations_for(session_factory, ctx.tenant_id, order_id)
    assert len(recs) == 1


async def test_dispensed_prescription_triggers_check_under_rx_context(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    catalog_service: CatalogService,
    clinical_service: ClinicalService,
    prescription_service: PrescriptionService,
    ctx: RequestContext,
) -> None:
    await _enable_ai(clinical_service, ctx)
    await _seed_interaction(session_factory, "Warfarin", "Aspirin", InteractionSeverity.MAJOR)
    warfarin = await _new_ingredient(session_factory, "Warfarin")
    aspirin = await _new_ingredient(session_factory, "Aspirin")
    drug_a = await _new_drug(catalog_service, ctx, "Thuốc W", [warfarin.id])
    drug_b = await _new_drug(catalog_service, ctx, "Thuốc A", [aspirin.id])

    def _item(drug_id: UUID) -> PrescriptionItemInput:
        return PrescriptionItemInput(
            drug_id=drug_id, quantity=Decimal("1"), dose="1", frequency="1", duration="1"
        )

    rx = await prescription_service.create_prescription(
        CreatePrescriptionInput(
            customer_id=uuid4(),
            doctor_name="BS. Test",
            items=[_item(drug_a), _item(drug_b)],
        ),
        ctx,
    )

    await event_bus.publish(PrescriptionDispensed(tenant_id=ctx.tenant_id, prescription_id=rx.id))

    recs = await _recommendations_for(session_factory, ctx.tenant_id, rx.id)
    assert len(recs) == 1
    assert recs[0].context_type == AiContextType.RX.value


async def test_unknown_dispensed_prescription_is_ignored(
    wired_container: Container,
    event_bus: InMemoryEventBus,
    session_factory: async_sessionmaker[AsyncSession],
    clinical_service: ClinicalService,
    ctx: RequestContext,
) -> None:
    await _enable_ai(clinical_service, ctx)
    # Prescription id that was never persisted → handler 404s internally and skips.
    await event_bus.publish(PrescriptionDispensed(tenant_id=ctx.tenant_id, prescription_id=uuid4()))
    assert await _count_recommendations(session_factory, ctx.tenant_id) == 0
