"""Analytics HTTP endpoints: reorder suggestions + dashboard (PROJECT_STATE §7am).

Reorder is a two-phase, human-in-the-loop flow ("cảnh báo không chặn"):
``POST /analytics/reorder/run`` recomputes suggestions, a human reviews
``GET .../suggestions``, then turns one into a DRAFT purchase order with
``.../{id}/materialize`` (never auto-sent) or ``.../{id}/dismiss``. ``run`` and the
two actions need ``analytics.reorder.run``; reads need ``analytics.read``.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.analytics.application import AnalyticsService
from pharmacy_os.modules.analytics.domain import SuggestionStatus
from pharmacy_os.modules.analytics.interface.schemas import (
    DashboardResponse,
    MaterializeResponse,
    ReorderRunResponse,
    SuggestionResponse,
)

ContextDep = Callable[..., Awaitable[RequestContext]]
"""``get_context`` là **async** kể từ audit B-07: nó phải tra CSDL để xác nhận cặp
``(tenant, chi nhánh)`` là có thật. FastAPI tự await, nên route không phải đổi gì."""


def _service(request: Request) -> AnalyticsService:
    service: AnalyticsService = request.app.state.container.resolve(AnalyticsService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/analytics", tags=["analytics"])

    @router.post("/reorder/run", response_model=ReorderRunResponse)
    async def run_reorder(
        branch_id: UUID | None = Query(
            None, description="Chi nhánh (bỏ trống = chi nhánh của bạn)"
        ),
        service: AnalyticsService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> ReorderRunResponse:
        return ReorderRunResponse.of(await service.run_reorder(ctx, branch_id=branch_id))

    @router.get("/reorder/suggestions", response_model=list[SuggestionResponse])
    async def list_suggestions(
        branch_id: UUID | None = Query(
            None, description="Chi nhánh (bỏ trống = chi nhánh của bạn)"
        ),
        status_filter: SuggestionStatus | None = Query(
            None, alias="status", description="Lọc theo trạng thái"
        ),
        service: AnalyticsService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> list[SuggestionResponse]:
        items = await service.list_suggestions(ctx, branch_id=branch_id, status=status_filter)
        return [SuggestionResponse.of(s) for s in items]

    @router.post(
        "/reorder/suggestions/{suggestion_id}/materialize", response_model=MaterializeResponse
    )
    async def materialize(
        suggestion_id: UUID,
        service: AnalyticsService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> MaterializeResponse:
        return MaterializeResponse.of(await service.materialize(suggestion_id, ctx))

    @router.post("/reorder/suggestions/{suggestion_id}/undo", response_model=SuggestionResponse)
    async def undo(
        suggestion_id: UUID,
        service: AnalyticsService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SuggestionResponse:
        """Hoàn tác việc tạo đơn mua nháp: huỷ đơn nháp, đề xuất về lại PENDING.

        Không nhận ``po_id`` từ client — đơn cần huỷ đọc từ chính bản ghi đề xuất."""
        return SuggestionResponse.of(await service.undo_materialize(suggestion_id, ctx))

    @router.post("/reorder/suggestions/{suggestion_id}/dismiss", response_model=SuggestionResponse)
    async def dismiss(
        suggestion_id: UUID,
        service: AnalyticsService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SuggestionResponse:
        return SuggestionResponse.of(await service.dismiss(suggestion_id, ctx))

    @router.get("/dashboard", response_model=DashboardResponse)
    async def dashboard(
        date_from: date = Query(..., description="Từ ngày (bao gồm)"),
        date_to: date = Query(..., description="Đến ngày (bao gồm)"),
        branch_id: UUID | None = Query(
            None, description="Chi nhánh (bỏ trống = chi nhánh của bạn)"
        ),
        service: AnalyticsService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> DashboardResponse:
        out = await service.dashboard(
            ctx, date_from=date_from, date_to=date_to, branch_id=branch_id
        )
        return DashboardResponse.of(out)

    return router


__all__ = ["build_router", "ContextDep"]
