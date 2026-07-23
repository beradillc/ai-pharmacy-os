"""Catalog HTTP endpoints."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.catalog.interface.schemas import (
    ActiveIngredientResponse,
    CreateDrugRequest,
    CreateIngredientRequest,
    DrugResponse,
)

ContextDep = Callable[..., RequestContext]


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
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[DrugResponse]:
        items = await service.list_drugs(ctx, limit=limit, offset=offset)
        return [DrugResponse.of(o) for o in items]

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
