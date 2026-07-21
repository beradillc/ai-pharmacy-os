"""Mapping between clinical ORM rows and domain entities."""

from __future__ import annotations

from pharmacy_os.modules.clinical.domain import (
    AiContextType,
    AiRecommendation,
    DrugInteraction,
    InteractionSeverity,
)
from pharmacy_os.modules.clinical.infrastructure.models import (
    AiRecommendationORM,
    DrugInteractionORM,
)


def interaction_to_domain(row: DrugInteractionORM) -> DrugInteraction:
    return DrugInteraction(
        id=row.id,
        ingredient_a=row.ingredient_a,
        ingredient_b=row.ingredient_b,
        severity=InteractionSeverity(row.severity),
        mechanism=row.mechanism,
        management=row.management,
        source=row.source,
    )


def interaction_to_orm(interaction: DrugInteraction) -> DrugInteractionORM:
    return DrugInteractionORM(
        id=interaction.id,
        ingredient_a=interaction.ingredient_a,
        ingredient_b=interaction.ingredient_b,
        severity=interaction.severity.value,
        mechanism=interaction.mechanism,
        management=interaction.management,
        source=interaction.source,
    )


def recommendation_to_domain(row: AiRecommendationORM) -> AiRecommendation:
    return AiRecommendation(
        id=row.id,
        tenant_id=row.tenant_id,
        context_type=AiContextType(row.context_type),
        context_id=row.context_id,
        model=row.model,
        prompt_hash=row.prompt_hash,
        confidence=row.confidence,
        requires_review=row.requires_review,
        output=row.output,
        sources=tuple(row.sources),
        accepted_by=row.accepted_by,
        created_at=row.created_at,
    )


def recommendation_to_orm(rec: AiRecommendation) -> AiRecommendationORM:
    return AiRecommendationORM(
        id=rec.id,
        tenant_id=rec.tenant_id,
        context_type=rec.context_type.value,
        context_id=rec.context_id,
        model=rec.model,
        prompt_hash=rec.prompt_hash,
        confidence=rec.confidence,
        requires_review=rec.requires_review,
        output=rec.output,
        sources=list(rec.sources),
        accepted_by=rec.accepted_by,
        created_at=rec.created_at,
    )
