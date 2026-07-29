"""Crm HTTP endpoints."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.crm.application import CrmService
from pharmacy_os.modules.crm.interface.schemas import (
    AddAllergyRequest,
    AddConditionRequest,
    CreateCustomerRequest,
    CustomerExportResponse,
    CustomerResponse,
    RecordConsentRequest,
)

ContextDep = Callable[..., Awaitable[RequestContext]]
"""``get_context`` là **async** kể từ audit B-07: nó phải tra CSDL để xác nhận cặp
``(tenant, chi nhánh)`` là có thật. FastAPI tự await, nên route không phải đổi gì."""


def _service(request: Request) -> CrmService:
    service: CrmService = request.app.state.container.resolve(CrmService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/customers", tags=["crm"])

    @router.get("/{customer_id}/export", response_model=CustomerExportResponse)
    async def export_customer(
        customer_id: UUID,
        service: CrmService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> CustomerExportResponse:
        """Right of access (Luật 91/2025 Điều 13-14). Requires ``crm.sensitive.read``."""
        return CustomerExportResponse.of(await service.export_customer_data(customer_id, ctx))

    @router.post("/{customer_id}/anonymise", response_model=CustomerResponse)
    async def anonymise_customer(
        customer_id: UUID,
        service: CrmService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> CustomerResponse:
        """Right of erasure, resolved as de-identification (duyệt Q2).

        Not ``DELETE``: the row survives, carrying the dispensing lines GPP requires
        be kept. Calling it ``DELETE`` would promise something the law forbids doing.
        """
        return CustomerResponse.of(await service.anonymise_customer(customer_id, ctx))

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
        phone: str | None = Query(
            None,
            description=(
                "Tra theo ĐÚNG số điện thoại. Không khớp một phần, và không có tìm "
                "theo tên — cột được mã hoá at-rest, xem CrmService.find_customer_by_phone."
            ),
        ),
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ) -> list[CustomerResponse]:
        # Trả DANH SÁCH 0 hoặc 1 phần tử thay vì 404 khi không thấy: màn Bán hàng
        # gõ số điện thoại từng chữ, nên "chưa thấy" là trạng thái BÌNH THƯỜNG
        # của mọi lần gõ dở. Bắt nó là lỗi thì mỗi phím bấm sinh một dòng đỏ.
        if phone is not None:
            found = await service.find_customer_by_phone(phone, ctx)
            return [] if found is None else [CustomerResponse.of(found)]
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
