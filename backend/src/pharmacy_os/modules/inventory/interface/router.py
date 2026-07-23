"""Inventory HTTP endpoints."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.interface.schemas import (
    DispenseRequest,
    DispenseResponse,
    NearExpiryResponse,
    OnHandResponse,
    ReceiptResponse,
    ReceiveStockRequest,
    ReconciliationResponse,
)

ContextDep = Callable[..., RequestContext]


def _service(request: Request) -> InventoryService:
    service: InventoryService = request.app.state.container.resolve(InventoryService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/inventory", tags=["inventory"])

    @router.post("/receive", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
    async def receive(
        body: ReceiveStockRequest,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> ReceiptResponse:
        return ReceiptResponse.of(await service.receive_stock(body.to_input(), ctx))

    @router.post("/dispense", response_model=DispenseResponse)
    async def dispense(
        body: DispenseRequest,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> DispenseResponse:
        return DispenseResponse.of(await service.dispense_stock(body.to_input(), ctx))

    @router.get("/on-hand", response_model=OnHandResponse)
    async def on_hand(
        drug_id: UUID,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> OnHandResponse:
        qty = await service.on_hand(drug_id, ctx)
        return OnHandResponse(drug_id=drug_id, on_hand=qty)

    @router.get("/alerts/near-expiry", response_model=list[NearExpiryResponse])
    async def near_expiry(
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        within_days: int = Query(90, ge=1, le=1000),
    ) -> list[NearExpiryResponse]:
        items = await service.list_near_expiry(ctx, within_days=within_days)
        return [NearExpiryResponse.of(i) for i in items]

    @router.get("/reconciliations", response_model=list[ReconciliationResponse])
    async def list_reconciliations(
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        resolved: bool | None = Query(default=None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[ReconciliationResponse]:
        items = await service.list_reconciliations(
            ctx, resolved=resolved, limit=limit, offset=offset
        )
        return [ReconciliationResponse.of(i) for i in items]

    @router.post(
        "/reconciliations/{reconciliation_id}/resolve", response_model=ReconciliationResponse
    )
    async def resolve_reconciliation(
        reconciliation_id: UUID,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> ReconciliationResponse:
        out = await service.resolve_reconciliation(reconciliation_id, ctx)
        return ReconciliationResponse.of(out)

    return router
