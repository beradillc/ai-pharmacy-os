"""Prescription HTTP endpoints (intake, pharmacist validate/reject, dispense)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.interface.schemas import (
    CreatePrescriptionRequest,
    PrescriptionResponse,
    RejectPrescriptionRequest,
)

ContextDep = Callable[..., RequestContext]


def _service(request: Request) -> PrescriptionService:
    service: PrescriptionService = request.app.state.container.resolve(PrescriptionService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    root = APIRouter(prefix="/prescriptions", tags=["prescription"])

    @root.post("", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
    async def create_prescription(
        body: CreatePrescriptionRequest,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(await service.create_prescription(body.to_input(), ctx))

    @root.get("/{prescription_id}", response_model=PrescriptionResponse)
    async def get_prescription(
        prescription_id: UUID,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(await service.get_prescription(prescription_id, ctx))

    @root.post("/{prescription_id}/validate", response_model=PrescriptionResponse)
    async def validate_prescription(
        prescription_id: UUID,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(await service.validate_prescription(prescription_id, ctx))

    @root.post("/{prescription_id}/reject", response_model=PrescriptionResponse)
    async def reject_prescription(
        prescription_id: UUID,
        body: RejectPrescriptionRequest,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(
            await service.reject_prescription(prescription_id, body.reason, ctx)
        )

    @root.post("/{prescription_id}/dispense", response_model=PrescriptionResponse)
    async def dispense_prescription(
        prescription_id: UUID,
        service: PrescriptionService = Depends(_service),
        ctx: RequestContext = Depends(get_context),
    ) -> PrescriptionResponse:
        return PrescriptionResponse.of(await service.dispense_prescription(prescription_id, ctx))

    return root
