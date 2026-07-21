"""SQLAlchemy implementations of the clinical repository ports.

``drug_interactions`` is global reference data (no tenant scope); ``ai_recommendations``
is tenant-scoped immutable audit — only ``accepted_by`` is ever updated after insert.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.clinical.domain import (
    AiRecommendation,
    DrugInteraction,
    normalize_ingredient,
)
from pharmacy_os.modules.clinical.infrastructure.mappers import (
    interaction_to_domain,
    interaction_to_orm,
    recommendation_to_domain,
    recommendation_to_orm,
)
from pharmacy_os.modules.clinical.infrastructure.models import (
    AiRecommendationORM,
    DrugInteractionORM,
)


class SqlAlchemyDrugInteractionRepository:
    """Global (not tenant-scoped) access to ``drug_interactions``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, interaction: DrugInteraction) -> None:
        self._session.add(interaction_to_orm(interaction))
        await self._session.flush()

    async def find_for_ingredients(self, ingredients: Sequence[str]) -> list[DrugInteraction]:
        keys = [normalize_ingredient(name) for name in ingredients]
        if not keys:
            return []
        stmt = select(DrugInteractionORM).where(
            DrugInteractionORM.ingredient_a.in_(keys),
            DrugInteractionORM.ingredient_b.in_(keys),
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [interaction_to_domain(row) for row in rows]


class SqlAlchemyAiRecommendationRepository:
    """Tenant-scoped persistence for :class:`AiRecommendation`."""

    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, recommendation: AiRecommendation) -> None:
        self._session.add(recommendation_to_orm(recommendation))
        await self._session.flush()

    async def get(self, recommendation_id: UUID) -> AiRecommendation | None:
        stmt = select(AiRecommendationORM).where(
            AiRecommendationORM.id == recommendation_id,
            AiRecommendationORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return recommendation_to_domain(row) if row is not None else None

    async def update(self, recommendation: AiRecommendation) -> None:
        stmt = select(AiRecommendationORM).where(
            AiRecommendationORM.id == recommendation.id,
            AiRecommendationORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        # Immutable audit record: only the human-in-the-loop sign-off can change.
        row.accepted_by = recommendation.accepted_by
        await self._session.flush()
