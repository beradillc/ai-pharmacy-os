"""Catalog HTTP endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.catalog.interface.schemas import (
    ActiveIngredientResponse,
    CreateDrugRequest,
    CreateIngredientRequest,
    DrugResponse,
    PriceHistoryResponse,
    ReplaceDrugIngredientsRequest,
    SetDrugPriceRequest,
)

ContextDep = Callable[..., Awaitable[RequestContext]]
"""``get_context`` là **async** kể từ audit B-07: nó phải tra CSDL để xác nhận cặp
``(tenant, chi nhánh)`` là có thật. FastAPI tự await, nên route không phải đổi gì."""


def _service(request: Request) -> CatalogService:
    service: CatalogService = request.app.state.container.resolve(CatalogService)
    return service


def _build_drugs_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/drugs", tags=["catalog"])

    @router.post("", response_model=DrugResponse, status_code=status.HTTP_201_CREATED)
    async def create_drug(
        body: CreateDrugRequest,
        service: CatalogService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> DrugResponse:
        out = await service.create_drug(body.to_input(), ctx)
        return DrugResponse.of(out)

    @router.get("", response_model=list[DrugResponse])
    async def list_drugs(
        service: CatalogService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        search: str | None = Query(default=None, max_length=255),
        ids: list[UUID] | None = Query(default=None),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[DrugResponse]:
        """Danh mục thuốc. ``search`` = một phần tên hoặc đúng mã vạch;
        ``ids`` = lặp lại tham số (``?ids=…&ids=…``) để gắn tên cho một trang dữ
        liệu chỉ có id — một lượt gọi, không phải một lượt mỗi dòng."""
        items = await service.list_drugs(ctx, search=search, ids=ids, limit=limit, offset=offset)
        return [DrugResponse.of(o) for o in items]

    @router.put("/{drug_id}/ingredients", response_model=DrugResponse)
    async def replace_drug_ingredients(
        drug_id: UUID,
        body: ReplaceDrugIngredientsRequest,
        service: CatalogService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> DrugResponse:
        """Đặt lại toàn bộ hoạt chất của một thuốc — sửa nhầm, bổ sung thiếu, xoá sai.

        ``PUT`` chứ không ``PATCH``: thân yêu cầu **là** danh sách mới, đầy đủ, nên gọi
        hai lần cùng một thân cho cùng một kết quả. ``PATCH`` sẽ hàm ý "trộn vào cái đang
        có", mà trộn thì không có cách nào diễn đạt *bỏ* một hoạt chất.

        Là tài nguyên con ``/ingredients`` chứ không phải ``PUT /drugs/{id}``: chỉ động
        tới đúng một thứ, nên không có đường nào để một lượt sửa hoạt chất vô tình ghi đè
        tên, giá hay mã vạch.

        Quyền ``catalog.update`` (cấp chuỗi). Trả 404 nếu thuốc không thuộc nhà thuốc hoặc
        một ``ingredient_id`` không có trong danh mục hoạt chất; 422 nếu danh sách trùng
        hoạt chất.
        """
        out = await service.replace_drug_ingredients(drug_id, body.to_input(), ctx)
        return DrugResponse.of(out)

    @router.put("/{drug_id}/price", response_model=DrugResponse)
    async def set_drug_price(
        drug_id: UUID,
        body: SetDrugPriceRequest,
        service: CatalogService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> DrugResponse:
        """Đặt lại giá bán niêm yết. Mỗi lần đổi ghi một dòng vào ``drug_price_history``.

        Là tài nguyên con ``/price`` chứ không ``PUT /drugs/{id}``, cùng lý do
        ``/ingredients``: chỉ động tới đúng một thứ, nên không có đường nào để một lượt
        đổi giá vô tình ghi đè tên, mã vạch hay hoạt chất.

        Quyền ``catalog.update`` (**cấp chuỗi**) — giá là quyết định của chủ chuỗi, không
        phải của quầy (Chain chốt 2026-07-31). Trả 404 nếu thuốc không thuộc nhà thuốc;
        422 nếu giá âm/lẻ quá 2 chữ số thập phân, trùng giá đang có, hoặc **đổi giá một mã
        đã có giá mà không ghi lý do**.
        """
        out = await service.set_drug_price(drug_id, body.new_price, body.reason, ctx)
        return DrugResponse.of(out)

    @router.get("/{drug_id}/price-history", response_model=list[PriceHistoryResponse])
    async def drug_price_history(
        drug_id: UUID,
        service: CatalogService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        limit: int = Query(50, ge=1, le=200),
    ) -> list[PriceHistoryResponse]:
        """Lịch sử giá của một thuốc, **mới nhất trước**.

        Quyền ``catalog.read``, không phải ``catalog.update``: giá niêm yết phải công khai
        tại nơi bán (Điều 107.4 Luật Dược), nên lịch sử của nó không phải bí mật với người
        trong nhà thuốc. Ai được **đổi** mới là chuyện cấp chuỗi.
        """
        return [
            PriceHistoryResponse.of(o)
            for o in await service.drug_price_history(drug_id, ctx, limit=limit)
        ]

    @router.get("/{drug_id}", response_model=DrugResponse)
    async def get_drug(
        drug_id: UUID,
        service: CatalogService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> DrugResponse:
        return DrugResponse.of(await service.get_drug(drug_id, ctx))

    return router


def _build_ingredients_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/active-ingredients", tags=["catalog"])

    @router.post("", response_model=ActiveIngredientResponse, status_code=status.HTTP_201_CREATED)
    async def create_ingredient(
        body: CreateIngredientRequest,
        service: CatalogService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> ActiveIngredientResponse:
        out = await service.create_ingredient(body.to_input(), ctx)
        return ActiveIngredientResponse.of(out)

    @router.get("", response_model=list[ActiveIngredientResponse])
    async def list_ingredients(
        service: CatalogService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> list[ActiveIngredientResponse]:
        items = await service.list_ingredients(ctx)
        return [ActiveIngredientResponse.of(o) for o in items]

    return router


def build_router(get_context: ContextDep) -> APIRouter:
    parent = APIRouter()
    parent.include_router(_build_drugs_router(get_context))
    parent.include_router(_build_ingredients_router(get_context))
    return parent
