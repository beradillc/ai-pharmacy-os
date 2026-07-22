"""Pydantic request/response schemas for clinical (drug-interaction check + AI audit)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from pharmacy_os.modules.clinical.application.dto import (
    AiRecommendationOutput,
    CheckInteractionsInput,
    DrugInteractionOutput,
    InteractionCheckResult,
    SetTenantAiSettingsInput,
    TenantAiSettingsOutput,
)
from pharmacy_os.modules.clinical.domain import AiContextType


class CheckInteractionsRequest(BaseModel):
    """Request an interaction check for an explicit list of active ingredients.

    Ingredients are passed by name — mapping a ``drug_id`` to its ingredients depends
    on a catalog ingredient model that does not exist yet (see module ``# BLOCKER``).
    """

    ingredients: list[str] = Field(min_length=1)
    context_type: AiContextType = AiContextType.SALE
    context_id: UUID | None = None

    @field_validator("ingredients")
    @classmethod
    def _strip_non_empty(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("Cần ít nhất một hoạt chất không rỗng")
        return cleaned

    def to_input(self) -> CheckInteractionsInput:
        return CheckInteractionsInput(
            ingredients=self.ingredients,
            context_type=self.context_type,
            context_id=self.context_id,
        )


class DrugInteractionResponse(BaseModel):
    ingredient_a: str
    ingredient_b: str
    severity: str
    mechanism: str
    management: str
    source: str

    @classmethod
    def of(cls, finding: DrugInteractionOutput) -> DrugInteractionResponse:
        return cls(
            ingredient_a=finding.ingredient_a,
            ingredient_b=finding.ingredient_b,
            severity=finding.severity,
            mechanism=finding.mechanism,
            management=finding.management,
            source=finding.source,
        )


class AiRecommendationResponse(BaseModel):
    id: UUID
    context_type: str
    context_id: UUID | None
    model: str
    confidence: float
    requires_review: bool
    output: str
    sources: list[str]
    accepted_by: UUID | None
    created_at: datetime

    @classmethod
    def of(cls, rec: AiRecommendationOutput) -> AiRecommendationResponse:
        return cls(
            id=rec.id,
            context_type=rec.context_type,
            context_id=rec.context_id,
            model=rec.model,
            confidence=rec.confidence,
            requires_review=rec.requires_review,
            output=rec.output,
            sources=list(rec.sources),
            accepted_by=rec.accepted_by,
            created_at=rec.created_at,
        )


class InteractionCheckResponse(BaseModel):
    """Deterministic findings (ranked, with source) + the audited AI recommendation."""

    findings: list[DrugInteractionResponse]
    recommendation: AiRecommendationResponse

    @classmethod
    def of(cls, result: InteractionCheckResult) -> InteractionCheckResponse:
        return cls(
            findings=[DrugInteractionResponse.of(f) for f in result.findings],
            recommendation=AiRecommendationResponse.of(result.recommendation),
        )


class SetTenantAiSettingsRequest(BaseModel):
    enable_clinical_ai: bool

    def to_input(self) -> SetTenantAiSettingsInput:
        return SetTenantAiSettingsInput(enable_clinical_ai=self.enable_clinical_ai)


class TenantAiSettingsResponse(BaseModel):
    tenant_id: UUID
    enable_clinical_ai: bool

    @classmethod
    def of(cls, out: TenantAiSettingsOutput) -> TenantAiSettingsResponse:
        return cls(tenant_id=out.tenant_id, enable_clinical_ai=out.enable_clinical_ai)
