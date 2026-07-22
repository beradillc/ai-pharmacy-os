"""Clinical data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pharmacy_os.modules.clinical.domain import (
    AiContextType,
    AiRecommendation,
    DrugInteraction,
    TenantAiSettings,
)


@dataclass(slots=True)
class CheckInteractionsInput:
    """Request to check drug–drug interactions for an explicit ingredient list.

    Mapping a sold/prescribed ``drug_id`` to its active ingredients is a separate,
    still-blocked concern (catalog has no ingredient model yet); callers pass
    ingredient names directly here.
    """

    ingredients: list[str]
    context_type: AiContextType
    context_id: UUID | None = None


@dataclass(slots=True)
class DrugInteractionOutput:
    ingredient_a: str
    ingredient_b: str
    severity: str
    mechanism: str
    management: str
    source: str

    @classmethod
    def of(cls, interaction: DrugInteraction) -> DrugInteractionOutput:
        return cls(
            ingredient_a=interaction.ingredient_a,
            ingredient_b=interaction.ingredient_b,
            severity=interaction.severity.value,
            mechanism=interaction.mechanism,
            management=interaction.management,
            source=interaction.source,
        )


@dataclass(slots=True)
class AiRecommendationOutput:
    id: UUID
    context_type: str
    context_id: UUID | None
    model: str
    confidence: float
    requires_review: bool
    output: str
    sources: tuple[str, ...]
    accepted_by: UUID | None
    created_at: datetime

    @classmethod
    def of(cls, rec: AiRecommendation) -> AiRecommendationOutput:
        return cls(
            id=rec.id,
            context_type=rec.context_type.value,
            context_id=rec.context_id,
            model=rec.model,
            confidence=rec.confidence,
            requires_review=rec.requires_review,
            output=rec.output,
            sources=rec.sources,
            accepted_by=rec.accepted_by,
            created_at=rec.created_at,
        )


@dataclass(slots=True)
class InteractionCheckResult:
    """Findings (deterministic, ranked) plus the audited AI recommendation for them."""

    findings: list[DrugInteractionOutput]
    recommendation: AiRecommendationOutput


@dataclass(slots=True)
class SetTenantAiSettingsInput:
    enable_clinical_ai: bool


@dataclass(slots=True)
class TenantAiSettingsOutput:
    tenant_id: UUID
    enable_clinical_ai: bool

    @classmethod
    def of(cls, settings: TenantAiSettings) -> TenantAiSettingsOutput:
        return cls(tenant_id=settings.tenant_id, enable_clinical_ai=settings.enable_clinical_ai)
