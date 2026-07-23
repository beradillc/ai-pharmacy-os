"""Crm HTTP endpoints."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.crm.application import CrmService
from pharmacy_os.modules.crm.interface.schemas import (
    AddAllergyRequest,
    AddConditionRequest,
    CreateCustomerRequest,
    CustomerResponse,
    RecordConsentRequest,
)

ContextDep = Callable[..., RequestContext]


def _service(request: Request) -> CrmService:
    service: CrmService = request.app.state.container.resolve(CrmService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/customers", tags=["crm"])

    @router.post(
        "/{customer_id}/consents",
        response_model=CustomerResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def record_consent(
        customer_id: UUID,
        body: RecordConsentRequest,
        service: CrmService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> CustomerResponse:
        """Record a consent decision (grant or revoke) for one purpose.

        Pulled in ahead of the rest of the interface layer: without it the API can
        create a customer but can never record an allergy, which is not a state worth
        committing.
        """
        out = await service.record_consent(customer_id, body.to_input(), ctx)
        return CustomerResponse.of(out)

    @router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
    async def create_customer(
        body: CreateCustomerRequest,
        service: CrmService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> CustomerResponse:
        out = await service.create_customer(body.to_input(), ctx)
        return CustomerResponse.of(out)

    @router.get("", response_model=list[CustomerResponse])
    async def list_customers(
        service: CrmService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[CustomerResponse]:
        items = await service.list_customers(ctx, limit=limit, offset=offset)
        return [CustomerResponse.of(o) for o in items]

    @router.get("/{customer_id}", response_model=CustomerResponse)
    async def get_customer(
        customer_id: UUID,
        service: CrmService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> CustomerResponse:
        return CustomerResponse.of(await service.get_customer(customer_id, ctx))

    @router.post(
        "/{customer_id}/allergies",
        response_model=CustomerResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def add_allergy(
        customer_id: UUID,
        body: AddAllergyRequest,
        service: CrmService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> CustomerResponse:
        out = await service.add_allergy(customer_id, body.to_input(), ctx)
        return CustomerResponse.of(out)

    @router.post(
        "/{customer_id}/conditions",
        response_model=CustomerResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def add_condition(
        customer_id: UUID,
        body: AddConditionRequest,
        service: CrmService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> CustomerResponse:
        out = await service.add_condition(customer_id, body.to_input(), ctx)
        return CustomerResponse.of(out)

    return router
