"""Clinical HTTP endpoints: interaction check + pharmacist sign-off of AI recommendations.

The response always carries the reference ``source`` per finding and the model's
``confidence`` — the safety verdict is the deterministic engine's, the LLM only explains
(a mock provider in S5.5, see ``# BLOCKER: AI__API_KEY thật``).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.clinical.application import ClinicalService
from pharmacy_os.modules.clinical.interface.schemas import (
    AiRecommendationResponse,
    CheckInteractionsRequest,
    InteractionCheckResponse,
    SetTenantAiSettingsRequest,
    TenantAiSettingsResponse,
)

ContextDep = Callable[..., RequestContext]


def _service(request: Request) -> ClinicalService:
    service: ClinicalService = request.app.state.container.resolve(ClinicalService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    root = APIRouter(prefix="/clinical", tags=["clinical"])

    @root.post(
        "/check-interactions",
        response_model=InteractionCheckResponse,
        status_code=status.HTTP_200_OK,
    )
    async def check_interactions(
        body: CheckInteractionsRequest,
        service: ClinicalService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> InteractionCheckResponse:
        return InteractionCheckResponse.of(await service.check_interactions(body.to_input(), ctx))

    @root.get("/recommendations/{recommendation_id}", response_model=AiRecommendationResponse)
    async def get_recommendation(
        recommendation_id: UUID,
        service: ClinicalService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> AiRecommendationResponse:
        return AiRecommendationResponse.of(await service.get_recommendation(recommendation_id, ctx))

    @root.post(
        "/recommendations/{recommendation_id}/accept", response_model=AiRecommendationResponse
    )
    async def accept_recommendation(
        recommendation_id: UUID,
        service: ClinicalService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> AiRecommendationResponse:
        return AiRecommendationResponse.of(
            await service.accept_recommendation(recommendation_id, ctx)
        )

    @root.get("/settings", response_model=TenantAiSettingsResponse)
    async def get_tenant_ai_settings(
        service: ClinicalService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> TenantAiSettingsResponse:
        return TenantAiSettingsResponse.of(await service.get_tenant_ai_settings(ctx))

    @root.put("/settings", response_model=TenantAiSettingsResponse)
    async def set_tenant_ai_settings(
        body: SetTenantAiSettingsRequest,
        service: ClinicalService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> TenantAiSettingsResponse:
        return TenantAiSettingsResponse.of(
            await service.set_tenant_ai_settings(body.to_input(), ctx)
        )

    return root
