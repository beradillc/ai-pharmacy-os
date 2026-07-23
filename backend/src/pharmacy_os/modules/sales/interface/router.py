"""Sales HTTP endpoints (POS + offline sync)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse

from pharmacy_os.core.config import OrgSettings, Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.interface.receipt_rendering import render_pdf, render_thermal_k80
from pharmacy_os.modules.sales.interface.schemas import (
    CreateSaleRequest,
    ReceiptFormat,
    ReceiptResponse,
    SaleResponse,
)

ContextDep = Callable[..., RequestContext]


def _service(request: Request) -> SalesService:
    service: SalesService = request.app.state.container.resolve(SalesService)
    return service


def _org_settings(request: Request) -> OrgSettings:
    settings: Settings = request.app.state.container.resolve(Settings)
    return settings.org


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

    # In bill (S7, rút gọn): không VAT, chữ ký chỉ là khoảng trống trên giấy in.
    @sales.get("/{order_id}/receipt")
    async def get_receipt(
        order_id: UUID,
        fmt: ReceiptFormat = Query(default=ReceiptFormat.JSON, alias="format"),
        service: SalesService = Depends(_service),
        org: OrgSettings = Depends(_org_settings),
        ctx: RequestContext = Depends(get_context),
    ) -> Response:
        receipt = await service.get_receipt(order_id, ctx)
        if fmt is ReceiptFormat.THERMAL_K80:
            return PlainTextResponse(
                render_thermal_k80(receipt, org), media_type="text/plain; charset=utf-8"
            )
        if fmt is ReceiptFormat.PDF_A5:
            return Response(content=render_pdf(receipt, org, "A5"), media_type="application/pdf")
        if fmt is ReceiptFormat.PDF_A4:
            return Response(content=render_pdf(receipt, org, "A4"), media_type="application/pdf")
        return JSONResponse(content=ReceiptResponse.of(receipt).model_dump(mode="json"))

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
