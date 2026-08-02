"""Sales HTTP endpoints (POS + offline sync)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.responses import JSONResponse, PlainTextResponse

from pharmacy_os.core.config import OrgSettings, Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.sales.application import SalesService, VnpayConfirmOutcome
from pharmacy_os.modules.sales.domain import OrgProfile, OrgProfileProvider
from pharmacy_os.modules.sales.interface.receipt_rendering import render_pdf, render_thermal_k80
from pharmacy_os.modules.sales.interface.schemas import (
    AllergyCheckRequest,
    AllergyCheckResponse,
    CreateSaleRequest,
    ReceiptFormat,
    ReceiptResponse,
    RegisterReturnRequest,
    SaleListItemResponse,
    SaleResponse,
    VnpayInitiateResponse,
)

_log = structlog.get_logger("sales.receipt_org")

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


def _hoa_hai_nguon(moi_truong: OrgSettings, khai_bao: OrgProfile | None) -> OrgSettings:
    """Thông tin cơ sở **đã khai** thắng cấu hình môi trường, **theo từng trường** (N-1).

    Vì sao trộn theo trường chứ không lấy trọn một bên: một cơ sở có thể mới khai tên và
    địa chỉ mà chưa có mã số thuế. Lấy trọn bản khai thì tờ hoá đơn **mất dòng MST** đang
    in đúng từ trước — một bước lùi im lặng, đúng loại lỗi kỷ luật #17 gọi là *"hình dạng
    không đổi nhưng ngữ nghĩa đổi"*. Lấy trọn cấu hình thì cả màn Cài đặt vô nghĩa.

    Chuỗi rỗng và ``None`` được coi như nhau — *"khai rồi mà để trống"* và *"chưa khai"*
    đều có nghĩa là **không có gì để in**, và một dòng ``ĐT:`` cụt trên tờ giấy đưa khách
    thì tệ hơn là không có dòng nào.
    """
    if khai_bao is None:
        return moi_truong
    return OrgSettings(
        pharmacy_name=khai_bao.ten_co_so or moi_truong.pharmacy_name,
        address=khai_bao.dia_chi or moi_truong.address,
        phone=khai_bao.dien_thoai or moi_truong.phone,
        tax_code=khai_bao.ma_so_thue or moi_truong.tax_code,
    )


def build_router(
    get_context: ContextDep, org_profile: OrgProfileProvider | None = None
) -> APIRouter:
    root = APIRouter(tags=["sales"])
    sales = APIRouter(prefix="/sales")
    sync = APIRouter(prefix="/sync")

    async def dau_trang_hoa_don(
        request: Request, ctx: RequestContext = Depends(get_context)
    ) -> OrgSettings:
        """Đầu trang hoá đơn: bản khai của cơ sở, lùi về cấu hình môi trường khi thiếu.

        🔴 **Không để một lỗi tra cứu làm hỏng tờ hoá đơn.** Nếu cổng đọc ném lỗi (CSDL
        chớp, quyền lệch, tenant chưa có hàng cấu hình), hoá đơn vẫn phải in ra — nó là
        chứng từ khách đang đứng chờ ở quầy. Ghi log rồi lùi về cấu hình môi trường,
        đúng hành vi của mọi phiên bản trước bản vá này.
        """
        moi_truong = _org_settings(request)
        if org_profile is None:
            return moi_truong
        try:
            return _hoa_hai_nguon(moi_truong, await org_profile.profile_of(ctx.tenant_id))
        except Exception:  # noqa: BLE001 — xem docstring: hoá đơn không được hỏng vì việc này
            _log.warning("org_profile_loi_tra_cuu", tenant_id=str(ctx.tenant_id), exc_info=True)
            return moi_truong

    @sales.post("", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
    async def create_sale(
        body: CreateSaleRequest,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SaleResponse:
        return SaleResponse.of(await service.complete_sale(body.to_input(), ctx))

    # Đ-7: quầy hỏi TRƯỚC khi bán, lúc thêm thuốc vào đơn. Chỉ đọc — không tạo đơn,
    # không ghi gì. Quyền `sales.create` như create_sale: ai bán được thì phải thấy được
    # cảnh báo của đơn mình đang bán. KHÔNG thay cổng cưỡng chế ở complete_sale.
    @sales.post("/allergy-check", response_model=AllergyCheckResponse)
    async def check_allergy(
        body: AllergyCheckRequest,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> AllergyCheckResponse:
        return AllergyCheckResponse.of(
            await service.check_allergy_risk(body.customer_id, frozenset(body.drug_ids), ctx)
        )

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

    # Đăng ký TRƯỚC "/{order_id}" không phải để tránh va đường dẫn ("" và
    # "/{order_id}" không va nhau) mà để đọc theo đúng thứ tự người ta dùng:
    # danh sách trước, chi tiết sau.
    @sales.get("", response_model=list[SaleListItemResponse])
    async def list_sales(
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
        branch_id: UUID | None = Query(default=None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[SaleListItemResponse]:
        """Danh sách đơn bán, mới nhất trước.

        Bỏ trống ngày ⇒ **hôm nay** ở cả hai đầu: màn quầy mở ra là thấy ca đang
        chạy, không phải toàn bộ lịch sử. Muốn xem xa hơn thì truyền ngày, và
        khoảng ngày đóng cả hai đầu."""
        today = date.today()
        rows = await service.list_sales(
            ctx,
            date_from=date_from or today,
            date_to=date_to or today,
            branch_id=branch_id,
            limit=limit,
            offset=offset,
        )
        return [SaleListItemResponse.of(r) for r in rows]

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
        org: OrgSettings = Depends(dau_trang_hoa_don),
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
        if fmt is ReceiptFormat.PDF_K80:
            return Response(content=render_pdf(receipt, org, "K80"), media_type="application/pdf")
        return JSONResponse(content=ReceiptResponse.of(receipt).model_dump(mode="json"))

    # Offline-first sync entrypoint: idempotent on client_uuid, so replaying a
    # queued sale never creates a duplicate (200, not 201 — upsert semantics).
    @sync.post("/sales", response_model=SaleResponse)
    async def sync_sale(
        body: CreateSaleRequest,
        service: SalesService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SaleResponse:
        """Nhận một đơn đã bán offline. **Khoan dung hơn `POST /sales` đúng một điểm.**

        `require_known_drugs=False`: đơn ở đây đã bán rồi — tiền đã vào két, hàng đã ra
        khỏi kệ. Một mã thuốc bị gỡ khỏi danh mục **sau khi bán** mà làm đơn không đồng bộ
        được nữa là đổi một lỗi im lặng lấy một lỗi mất tiền (phương án B, GĐ chọn
        2026-07-31 dưới uỷ quyền của Chain — ba phương án ở PROJECT_STATE §7cl).

        Đây **không** phải lỗ hổng bỏ ngỏ: nó là một quyết định, và cái giá của nó — đơn
        mang thuốc lạ thì không trừ tồn kho nào ⇒ sổ sách lệch tồn kho — cần một báo cáo
        đối soát định kỳ để nhìn ra. Còn nợ, ghi ở §7co.
        """
        return SaleResponse.of(
            await service.complete_sale(body.to_input(), ctx, require_known_drugs=False)
        )

    root.include_router(sales)
    root.include_router(sync)
    return root
