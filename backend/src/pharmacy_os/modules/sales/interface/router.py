"""Sales HTTP endpoints (POS + offline sync)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse

from pharmacy_os.core.config import OrgSettings, Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.sales.application import SalesService, VnpayConfirmOutcome
from pharmacy_os.modules.sales.interface.receipt_rendering import render_pdf, render_thermal_k80
from pharmacy_os.modules.sales.interface.schemas import (
    CreateSaleRequest,
    ReceiptFormat,
    ReceiptResponse,
    RegisterReturnRequest,
    SaleResponse,
    VnpayInitiateResponse,
)

ContextDep = Callable[..., Awaitable[RequestContext]]
"""``get_context`` là **async** kể từ audit B-07: nó phải tra CSDL để xác nhận cặp
``(tenant, chi nhánh)`` là có thật. FastAPI tự await, nên route không phải đổi gì."""

#: VNPAY's own response-code vocabulary (not an HTTP status — VNPAY always expects
#: 200 OK with this body, and reads ``RspCode`` itself to decide whether to retry
#: the IPN). Codes are VNPAY's, not invented: "00"/"01"/"02"/"04"/"97" are the ones
#: their spec defines for exactly these situations; "99" is their catch-all.
_VNPAY_RSP: dict[VnpayConfirmOutcome, tuple[str, str]] = {
    VnpayConfirmOutcome.CONFIRMED: ("00", "Confirm Success"),
    VnpayConfirmOutcome.CANCELLED_RECORDED: ("00", "Confirm Success"),
    VnpayConfirmOutcome.ALREADY_CONFIRMED: ("02", "Order already confirmed"),
    VnpayConfirmOutcome.ORDER_NOT_PENDING: ("02", "Order already confirmed"),
    VnpayConfirmOutcome.ORDER_NOT_FOUND: ("01", "Order not found"),
    VnpayConfirmOutcome.AMOUNT_MISMATCH: ("04", "Invalid amount"),
    VnpayConfirmOutcome.INVALID_SIGNATURE: ("97", "Invalid signature"),
    VnpayConfirmOutcome.GATEWAY_NOT_CONFIGURED: ("99", "Unknown error"),
}


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

    # Sprint 8 mục 4/4 (payment_vnpay): authenticated like `create_sale` — a cashier
    # starts the checkout — but does not complete the order. See
    # SalesService.initiate_vnpay_payment for why this is the one place a DRAFT
    # order is ever persisted.
    @sales.post(
        "/vnpay/initiate", response_model=VnpayInitiateResponse, status_code=status.HTTP_201_CREATED
    )
    async def initiate_vnpay(
        body: CreateSaleRequest,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> VnpayInitiateResponse:
        return VnpayInitiateResponse.of(await service.initiate_vnpay_payment(body.to_input(), ctx))

    # VNPAY's IPN: a GET from VNPAY's own servers, not our authenticated users —
    # deliberately **no** `Depends(get_context)`. The gateway's HMAC signature
    # (checked inside confirm_vnpay_callback via the resolved PaymentGateway) is
    # the authentication for this endpoint; there is no JWT to require. Always
    # answers 200 with VNPAY's own RspCode vocabulary — VNPAY reads that body, not
    # the HTTP status, to decide whether to retry.
    @sales.get("/vnpay/callback")
    async def vnpay_callback(
        request: Request,
        service: SalesService = Depends(_service),
    ) -> JSONResponse:
        outcome = await service.confirm_vnpay_callback(dict(request.query_params))
        rsp_code, message = _VNPAY_RSP[outcome]
        return JSONResponse(content={"RspCode": rsp_code, "Message": message})

    @sales.get("/{order_id}", response_model=SaleResponse)
    async def get_sale(
        order_id: UUID,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SaleResponse:
        return SaleResponse.of(await service.get_sale(order_id, ctx))

    @sales.post("/{order_id}/returns", response_model=SaleResponse)
    async def register_return(
        order_id: UUID,
        body: RegisterReturnRequest,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SaleResponse:
        return SaleResponse.of(await service.register_return(order_id, body.to_input(), ctx))

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
