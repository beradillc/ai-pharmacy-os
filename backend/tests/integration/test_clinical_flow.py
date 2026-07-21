from collections.abc import Awaitable, Callable

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from pharmacy_os.modules.clinical.application import CheckInteractionsInput, ClinicalService
from pharmacy_os.modules.clinical.domain import (
    AiContextType,
    DrugInteraction,
    InteractionSeverity,
)
from pharmacy_os.modules.clinical.infrastructure import SqlAlchemyDrugInteractionRepository

SeedFn = Callable[[list[DrugInteraction]], Awaitable[None]]


@pytest.fixture
def seed_interactions(
    session_factory: async_sessionmaker[AsyncSession],
) -> SeedFn:
    async def _seed(interactions: list[DrugInteraction]) -> None:
        async with session_factory() as session:
            repo = SqlAlchemyDrugInteractionRepository(session)
            for interaction in interactions:
                await repo.add(interaction)
            await session.commit()

    return _seed


def _interaction(a: str, b: str, severity: InteractionSeverity) -> DrugInteraction:
    return DrugInteraction(
        ingredient_a=a,
        ingredient_b=b,
        severity=severity,
        mechanism="cơ chế mẫu",
        management="xử trí mẫu",
        source="test",
    )


async def test_check_ranks_findings_and_audits_recommendation(
    clinical_service: ClinicalService, ctx: RequestContext, seed_interactions: SeedFn
) -> None:
    await seed_interactions(
        [
            _interaction("Warfarin", "Aspirin", InteractionSeverity.MAJOR),
            _interaction("Ramipril", "Ibuprofen", InteractionSeverity.MODERATE),
            # Not both present in the query below → must be excluded.
            _interaction("Metformin", "Cimetidine", InteractionSeverity.MINOR),
        ]
    )

    result = await clinical_service.check_interactions(
        CheckInteractionsInput(
            ingredients=["aspirin", "warfarin", "ramipril", "ibuprofen"],
            context_type=AiContextType.SALE,
        ),
        ctx,
    )

    # Two findings, most-serious first; the MINOR pair (Cimetidine absent) is excluded.
    assert [f.severity for f in result.findings] == [
        InteractionSeverity.MAJOR.value,
        InteractionSeverity.MODERATE.value,
    ]
    # A MAJOR finding forces pharmacist review regardless of model confidence.
    assert result.recommendation.requires_review is True
    assert result.recommendation.accepted_by is None
    assert result.recommendation.context_type == AiContextType.SALE.value
    assert result.recommendation.model == "mock-llm"
    assert result.recommendation.sources == ("test",)


async def test_check_persists_recommendation_readable_back(
    clinical_service: ClinicalService, ctx: RequestContext, seed_interactions: SeedFn
) -> None:
    await seed_interactions([])
    result = await clinical_service.check_interactions(
        CheckInteractionsInput(ingredients=["paracetamol"], context_type=AiContextType.RX),
        ctx,
    )
    assert result.findings == []

    fetched = await clinical_service.get_recommendation(result.recommendation.id, ctx)
    assert fetched.id == result.recommendation.id
    assert fetched.sources == ()


async def test_no_findings_low_confidence_still_requires_review(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: object,
    ctx: RequestContext,
) -> None:
    from pharmacy_os.core.ai import MockLLMProvider
    from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
    from pharmacy_os.modules.clinical.infrastructure import SqlAlchemyAiRecommendationRepository

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)  # type: ignore[arg-type]

    service = ClinicalService(
        uow_factory,
        lambda uow: SqlAlchemyDrugInteractionRepository(uow.session),
        lambda uow, c: SqlAlchemyAiRecommendationRepository(uow.session, c),
        MockLLMProvider(confidence=0.2),  # below min_confidence
        min_confidence=0.6,
    )
    result = await service.check_interactions(
        CheckInteractionsInput(ingredients=["paracetamol"], context_type=AiContextType.CHAT),
        ctx,
    )
    # No findings, but low confidence trips the guardrail.
    assert result.findings == []
    assert result.recommendation.requires_review is True


async def test_accept_recommendation_human_in_the_loop(
    clinical_service: ClinicalService, ctx: RequestContext, seed_interactions: SeedFn
) -> None:
    await seed_interactions([_interaction("Warfarin", "Aspirin", InteractionSeverity.MAJOR)])
    result = await clinical_service.check_interactions(
        CheckInteractionsInput(
            ingredients=["warfarin", "aspirin"], context_type=AiContextType.SALE
        ),
        ctx,
    )
    accepted = await clinical_service.accept_recommendation(result.recommendation.id, ctx)
    assert accepted.accepted_by == ctx.user_id


async def test_accept_twice_is_conflict(
    clinical_service: ClinicalService, ctx: RequestContext, seed_interactions: SeedFn
) -> None:
    await seed_interactions([])
    result = await clinical_service.check_interactions(
        CheckInteractionsInput(ingredients=["paracetamol"], context_type=AiContextType.SALE),
        ctx,
    )
    await clinical_service.accept_recommendation(result.recommendation.id, ctx)
    with pytest.raises(ConflictError):
        await clinical_service.accept_recommendation(result.recommendation.id, ctx)


async def test_get_unknown_recommendation_raises(
    clinical_service: ClinicalService, ctx: RequestContext
) -> None:
    from uuid import uuid4

    with pytest.raises(NotFoundError):
        await clinical_service.get_recommendation(uuid4(), ctx)


async def test_check_requires_permission(
    clinical_service: ClinicalService, ctx: RequestContext
) -> None:
    unprivileged = RequestContext(
        tenant_id=ctx.tenant_id,
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=frozenset(),
    )
    with pytest.raises(PermissionDeniedError):
        await clinical_service.check_interactions(
            CheckInteractionsInput(ingredients=["aspirin"], context_type=AiContextType.SALE),
            unprivileged,
        )


async def test_recommendation_is_tenant_isolated(
    clinical_service: ClinicalService, ctx: RequestContext, seed_interactions: SeedFn
) -> None:
    from uuid import uuid4

    await seed_interactions([])
    result = await clinical_service.check_interactions(
        CheckInteractionsInput(ingredients=["paracetamol"], context_type=AiContextType.SALE),
        ctx,
    )
    other_tenant = RequestContext(
        tenant_id=uuid4(),
        branch_id=ctx.branch_id,
        user_id=ctx.user_id,
        permissions=ctx.permissions,
    )
    with pytest.raises(NotFoundError):
        await clinical_service.get_recommendation(result.recommendation.id, other_tenant)
