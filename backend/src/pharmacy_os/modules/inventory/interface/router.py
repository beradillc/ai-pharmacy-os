"""Inventory HTTP endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.interface.schemas import (
    DispenseRequest,
    DispenseResponse,
    LocationStockResponse,
    NearExpiryResponse,
    OnHandResponse,
    PickCandidateResponse,
    PutAwayRequest,
    PutAwayResponse,
    ReceiptResponse,
    ReceiveStockRequest,
    ReconciliationResponse,
    StockRowResponse,
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
