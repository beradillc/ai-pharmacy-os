"""Sales HTTP endpoints (POS + offline sync)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.interface.schemas import CreateSaleRequest, SaleResponse

ContextDep = Callable[..., RequestContext]


def _service(request: Request) -> SalesService:
    service: SalesService = request.app.state.container.resolve(SalesService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    root = APIRouter(tags=["sales"])
    sales = APIRouter(prefix="/sales")
    sync = APIRouter(prefix="/sync")

    @sales.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
    async def create_sale(
        body: CreateSaleRequest,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SaleResponse:
        return SaleResponse.of(await service.complete_sale(body.to_input(), ctx))

    @sales.get("/{order_id}", response_model=SaleResponse)
    async def get_sale(
        order_id: UUID,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SaleResponse:
        return SaleResponse.of(await service.get_sale(order_id, ctx))

    # Offline-first sync entrypoint: idempotent on client_uuid, so replaying a
    # queued sale never creates a duplicate (200, not 201 — upsert semantics).
    @sync.post("/sales", response_model=SaleResponse)
    async def sync_sale(
        body: CreateSaleRequest,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SaleResponse:
        return SaleResponse.of(await service.complete_sale(body.to_input(), ctx))

    root.include_router(sales)
    root.include_router(sync)
    return root
