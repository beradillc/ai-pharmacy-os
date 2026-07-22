"""Procurement HTTP endpoints: suppliers, purchase orders, goods receipt notes.

Three resource groups (docs/11 §procurement), each its own sub-router, combined
into one returned by :func:`build_router` — same convention as ``sales``
combining order create/get/sync under one module. Beyond the two POST routes
docs/11 lists explicitly (create PO, create GRN), the PO/GRN state-machine
transitions (``place``/``cancel``/``close``/``confirm``) get their own action
routes, mirroring the precedent set by ``/prescriptions/{id}/{validate,reject,
dispense}``.
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.procurement.application import ProcurementService
from pharmacy_os.modules.procurement.interface.schemas import (
    CreateGoodsReceiptRequest,
    CreatePurchaseOrderRequest,
    CreateSupplierRequest,
    GoodsReceiptResponse,
    PurchaseOrderItemRequest,
    PurchaseOrderResponse,
    SupplierResponse,
)

ContextDep = Callable[..., RequestContext]


def _service(request: Request) -> ProcurementService:
    service: ProcurementService = request.app.state.container.resolve(ProcurementService)
    return service


def _build_supplier_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/suppliers", tags=["procurement"])

    @router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED)
    async def create_supplier(
        body: CreateSupplierRequest,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SupplierResponse:
        return SupplierResponse.of(await service.create_supplier(body.to_input(), ctx))

    @router.get("", response_model=list[SupplierResponse])
    async def list_suppliers(
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[SupplierResponse]:
        items = await service.list_suppliers(ctx, limit=limit, offset=offset)
        return [SupplierResponse.of(o) for o in items]

    @router.get("/{supplier_id}", response_model=SupplierResponse)
    async def get_supplier(
        supplier_id: UUID,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> SupplierResponse:
        return SupplierResponse.of(await service.get_supplier(supplier_id, ctx))

    return router


def _build_purchase_order_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/purchase-orders", tags=["procurement"])

    @router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
    async def create_purchase_order(
        body: CreatePurchaseOrderRequest,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PurchaseOrderResponse:
        return PurchaseOrderResponse.of(await service.create_purchase_order(body.to_input(), ctx))

    @router.get("/{po_id}", response_model=PurchaseOrderResponse)
    async def get_purchase_order(
        po_id: UUID,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PurchaseOrderResponse:
        return PurchaseOrderResponse.of(await service.get_purchase_order(po_id, ctx))

    @router.post(
        "/{po_id}/items", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED
    )
    async def add_po_item(
        po_id: UUID,
        body: PurchaseOrderItemRequest,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PurchaseOrderResponse:
        return PurchaseOrderResponse.of(await service.add_po_item(po_id, body.to_input(), ctx))

    @router.post("/{po_id}/place", response_model=PurchaseOrderResponse)
    async def place_purchase_order(
        po_id: UUID,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PurchaseOrderResponse:
        return PurchaseOrderResponse.of(await service.mark_ordered(po_id, ctx))

    @router.post("/{po_id}/cancel", response_model=PurchaseOrderResponse)
    async def cancel_purchase_order(
        po_id: UUID,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PurchaseOrderResponse:
        return PurchaseOrderResponse.of(await service.cancel_purchase_order(po_id, ctx))

    @router.post("/{po_id}/close", response_model=PurchaseOrderResponse)
    async def close_purchase_order(
        po_id: UUID,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PurchaseOrderResponse:
        return PurchaseOrderResponse.of(await service.close_purchase_order(po_id, ctx))

    return router


def _build_goods_receipt_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/goods-receipts", tags=["procurement"])

    @router.post("", response_model=GoodsReceiptResponse, status_code=status.HTTP_201_CREATED)
    async def create_goods_receipt(
        body: CreateGoodsReceiptRequest,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> GoodsReceiptResponse:
        return GoodsReceiptResponse.of(await service.create_goods_receipt(body.to_input(), ctx))

    @router.get("/{grn_id}", response_model=GoodsReceiptResponse)
    async def get_goods_receipt(
        grn_id: UUID,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> GoodsReceiptResponse:
        return GoodsReceiptResponse.of(await service.get_goods_receipt(grn_id, ctx))

    @router.post("/{grn_id}/confirm", response_model=GoodsReceiptResponse)
    async def confirm_goods_receipt(
        grn_id: UUID,
        service: ProcurementService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> GoodsReceiptResponse:
        return GoodsReceiptResponse.of(await service.confirm_goods_receipt(grn_id, ctx))

    return router


def build_router(get_context: ContextDep) -> APIRouter:
    root = APIRouter()
    root.include_router(_build_supplier_router(get_context))
    root.include_router(_build_purchase_order_router(get_context))
    root.include_router(_build_goods_receipt_router(get_context))
    return root
