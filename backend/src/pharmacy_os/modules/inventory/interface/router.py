"""Inventory HTTP endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.domain.counting import CountStatus
from pharmacy_os.modules.inventory.interface.schemas import (
    AdjustStockRequest,
    ChangLayResponse,
    CountLineRequest,
    DispenseRequest,
    DispenseResponse,
    LocationStockResponse,
    LoTrinhRequest,
    LoTrinhResponse,
    NearExpiryResponse,
    OnHandResponse,
    OpenCountRequest,
    PickCandidateResponse,
    PutAwayRequest,
    PutAwayResponse,
    ReceiptResponse,
    ReceiveStockRequest,
    ReconciliationResponse,
    StockCountResponse,
    StockRowResponse,
    TomTatOResponse,
)

ContextDep = Callable[..., Awaitable[RequestContext]]
"""``get_context`` là **async** kể từ audit B-07: nó phải tra CSDL để xác nhận cặp
``(tenant, chi nhánh)`` là có thật. FastAPI tự await, nên route không phải đổi gì."""


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

    @router.post("/initialize", response_model=ReceiptResponse, status_code=status.HTTP_201_CREATED)
    async def initialize_stock(
        body: ReceiveStockRequest,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> ReceiptResponse:
        """**Khởi tạo tồn kho** — nhà thuốc mới, chuyển phần mềm, hoặc kiểm kê tổng.

        KHÔNG phải nhập mua: không đơn mua hàng, không hoá đơn, không nhà cung cấp. Ghi
        ``ref_type='INIT'`` để sổ chuyển động phân biệt được với hàng mua vào — xem
        ``ReceiveStockInput.is_initial`` về cái giá của việc trộn hai thứ.

        Thân yêu cầu giống hệt ``/receive``; đường riêng để **ý định** nằm ở URL chứ không
        nằm trong một cờ boolean mà bên gọi dễ quên. Quyền ``inventory.receive``.
        """
        data = body.to_input()
        data.is_initial = True
        return ReceiptResponse.of(await service.receive_stock(data, ctx))

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

    @router.get("/stock", response_model=list[StockRowResponse])
    async def list_stock(
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        branch_id: UUID | None = Query(default=None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[StockRowResponse]:
        """Tồn kho theo lô, **cận hạn lên trước**. Bỏ trống ``branch_id`` = toàn
        tenant (xem ``InventoryService.list_stock``)."""
        items = await service.list_stock(ctx, branch_id=branch_id, limit=limit, offset=offset)
        return [StockRowResponse.of(i) for i in items]

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

    # ── BERAS V2 Phase 2: tồn theo vị trí ────────────────────────────────────────

    @router.post("/put-away", response_model=PutAwayResponse, status_code=status.HTTP_201_CREATED)
    async def put_away(
        body: PutAwayRequest,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PutAwayResponse:
        """Cất hàng của một lô vào một ô.

        **Không tạo hàng mới** — hàng đã tồn tại từ lúc nhận; việc này chỉ nói ra nó đang
        nằm đâu. Ghi một ``StockMovement`` loại ``TRANSFER``, và ``TRANSFER`` cố ý không đổi
        tổng tồn.

        Quyền ``inventory.receive`` (cất hàng lên kệ là cùng một đôi tay với người nhận
        hàng). Trả **404** nếu lô/ô không thuộc chi nhánh; **422** nếu ô đã ngừng hoạt động
        hoặc xếp vượt tồn của lô.

        Phản hồi kèm ``chua_xep_o`` — số hàng của lô vẫn chưa có chỗ.
        """
        return PutAwayResponse.of(
            await service.put_away(
                batch_id=body.batch_id,
                location_id=body.location_id,
                quantity=body.quantity,
                ctx=ctx,
            )
        )

    @router.get("/where", response_model=list[PickCandidateResponse])
    async def where_is(
        drug_id: UUID,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> list[PickCandidateResponse]:
        """Thuốc này đang nằm ở ô nào — **đã sắp theo thứ tự lấy hàng**.

        FEFO trước, đường đi sau (GĐ chốt 2026-07-31). Màn hình **không được sắp lại**: mỗi
        chỗ tự sắp là mỗi chỗ có cơ hội sắp sai một kiểu khác nhau.

        Trả rỗng khi thuốc chưa được xếp vào ô nào — khác hẳn "kho hết hàng", và màn hình
        phải nói ra sự khác biệt đó.

        Quyền ``inventory.read``.
        """
        return [PickCandidateResponse.of(c) for c in await service.where_is(drug_id, ctx)]

    @router.get("/locations/summary", response_model=list[TomTatOResponse])
    async def tom_tat_moi_o(
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> list[TomTatOResponse]:
        """Tồn tóm tắt của **mọi ô đang giữ hàng** — một lượt gọi cho cả sơ đồ (Phase 12).

        Đặt TRƯỚC `/locations/{location_id}/stock`: FastAPI khớp route theo thứ tự khai báo,
        đặt sau thì `summary` bị nuốt thành một `location_id` và trả 422 vì không phải UUID.
        (Đúng cái bẫy `/prescriptions/archive` đã dính ngày 31/07.)

        Chỉ ô **có hàng** mới có dòng. Quyền ``inventory.read``.
        """
        return [TomTatOResponse.of(t) for t in await service.tom_tat_moi_o(ctx)]

    @router.post("/pick-route", response_model=LoTrinhResponse)
    async def lo_trinh_lay_hang(
        body: LoTrinhRequest,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> LoTrinhResponse:
        """Lộ trình đi lấy hàng cho **cả giỏ** — gộp theo ô, sắp theo đường đi (V2 Phase 4).

        Khác `GET /where` ở chỗ: `/where` trả lời *"một mã nằm ở đâu"*, cái này trả lời
        *"đi một vòng thì đi thế nào"*. Gộp theo **ô** chứ không theo mặt hàng — cái tốn
        công là đi tới ô.

        Mã không lấy đủ được nằm ở `thieu`, và lộ trình **vẫn trả về** cho phần lấy được:
        một giỏ mười mã mà một mã chưa xếp ô thì người đi lấy vẫn cần chín mã kia.

        Quyền ``inventory.read``.
        """
        chang, thieu = await service.lo_trinh_lay_hang(
            [(d.drug_id, d.quantity) for d in body.dong], ctx
        )
        return LoTrinhResponse(chang=[ChangLayResponse.of(c) for c in chang], thieu=thieu)

    # ── BERAS V2 Phase 11: kiểm kê theo ô ────────────────────────────────────────

    @router.post("/counts", response_model=StockCountResponse, status_code=status.HTTP_201_CREATED)
    async def open_count(
        body: OpenCountRequest,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StockCountResponse:
        """Mở phiên kiểm kê cho một ô. Quyền ``inventory.receive``."""
        return StockCountResponse.of(await service.open_count(body.location_id, ctx))

    @router.post("/adjust", response_model=StockCountResponse, status_code=status.HTTP_201_CREATED)
    async def adjust_stock(
        body: AdjustStockRequest,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StockCountResponse:
        """Điều chỉnh tồn một lô tại một ô **trong một lượt** (UAT lỗi M-07).

        Chạy trọn luồng kiểm kê đã có (mở → đếm → nộp → duyệt), chỉ gộp bốn lượt bấm. Vì
        vậy nó cần **cả hai** quyền: ``inventory.receive`` để đếm và ``inventory.reconcile``
        để duyệt — đường tắt không đi kèm ưu ái quyền hạn nào.

        Trả về phiên kiểm kê đã duyệt, để người dùng tra lại được phiếu bất cứ lúc nào.
        """
        out = await service.adjust_stock_at_location(
            location_id=body.location_id,
            batch_id=body.batch_id,
            actual_qty=body.actual_qty,
            reason=body.reason,
            ctx=ctx,
        )
        return StockCountResponse.of(out)

    @router.get("/counts", response_model=list[StockCountResponse])
    async def list_counts(
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        count_status: CountStatus | None = Query(default=None, alias="status"),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[StockCountResponse]:
        rows = await service.list_counts(ctx, status=count_status, limit=limit, offset=offset)
        return [StockCountResponse.of(p) for p in rows]

    @router.get("/counts/{count_id}", response_model=StockCountResponse)
    async def get_count(
        count_id: UUID,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StockCountResponse:
        return StockCountResponse.of(await service.get_count(count_id, ctx))

    @router.post("/counts/{count_id}/lines", response_model=StockCountResponse)
    async def count_line(
        count_id: UUID,
        body: CountLineRequest,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StockCountResponse:
        """Ghi số đếm được của một lô. 409 nếu phiên đã nộp."""
        out = await service.count_line(count_id, body.batch_id, body.counted_qty, ctx)
        return StockCountResponse.of(out)

    @router.post("/counts/{count_id}/submit", response_model=StockCountResponse)
    async def submit_count(
        count_id: UUID,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StockCountResponse:
        """Nộp phiên — chốt số sổ tại đúng thời điểm này. Chưa đụng tồn kho."""
        return StockCountResponse.of(await service.submit_count(count_id, ctx))

    @router.post("/counts/{count_id}/approve", response_model=StockCountResponse)
    async def approve_count(
        count_id: UUID,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StockCountResponse:
        """Duyệt — **đây** là lúc tồn kho đổi. Quyền ``inventory.reconcile``."""
        return StockCountResponse.of(await service.approve_count(count_id, ctx))

    @router.post("/counts/{count_id}/reject", response_model=StockCountResponse)
    async def reject_count(
        count_id: UUID,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StockCountResponse:
        """Từ chối — phiên ở lại trong sổ như một vết đã đếm, tồn kho không đổi."""
        return StockCountResponse.of(await service.reject_count(count_id, ctx))

    @router.get("/locations/{location_id}/stock", response_model=list[LocationStockResponse])
    async def stock_at_location(
        location_id: UUID,
        service: InventoryService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> list[LocationStockResponse]:
        """Ô này đang giữ những lô nào, hạn dùng nào, bao nhiêu.

        Quyền ``inventory.read``.
        """
        return [
            LocationStockResponse.of(r) for r in await service.stock_at_location(location_id, ctx)
        ]

    return router
