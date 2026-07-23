"""Compliance HTTP endpoints: sổ thuốc kiểm soát đặc biệt, cấu hình tenant, liên thông CSDL Dược."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.compliance.application import ComplianceService, NationalSyncService
from pharmacy_os.modules.compliance.interface.schemas import (
    ControlledLedgerEntryResponse,
    NationalSyncLogResponse,
    PushSyncRequest,
    RecordControlledEntryRequest,
    SetTenantComplianceConfigRequest,
    TenantComplianceConfigResponse,
)

ContextDep = Callable[..., RequestContext]


def _compliance_service(request: Request) -> ComplianceService:
    service: ComplianceService = request.app.state.container.resolve(ComplianceService)
    return service


def _sync_service(request: Request) -> NationalSyncService:
    service: NationalSyncService = request.app.state.container.resolve(NationalSyncService)
    return service


def build_router(get_context: ContextDep) -> APIRouter:
    router = APIRouter(prefix="/compliance", tags=["compliance"])

    @router.post(
        "/controlled-ledger",
        response_model=ControlledLedgerEntryResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def record_controlled_entry(
        body: RecordControlledEntryRequest,
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> ControlledLedgerEntryResponse:
        out = await service.record_controlled_entry(body.to_input(), ctx)
        return ControlledLedgerEntryResponse.of(out)

    @router.get("/controlled-ledger/{entry_id}", response_model=ControlledLedgerEntryResponse)
    async def get_ledger_entry(
        entry_id: UUID,
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> ControlledLedgerEntryResponse:
        out = await service.get_ledger_entry(entry_id, ctx)
        return ControlledLedgerEntryResponse.of(out)

    @router.put("/tenant-config", response_model=TenantComplianceConfigResponse)
    async def set_tenant_config(
        body: SetTenantComplianceConfigRequest,
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> TenantComplianceConfigResponse:
        out = await service.set_tenant_config(body.to_input(), ctx)
        return TenantComplianceConfigResponse.of(out)

    @router.get("/tenant-config", response_model=TenantComplianceConfigResponse)
    async def get_tenant_config(
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> TenantComplianceConfigResponse:
        out = await service.get_tenant_config(ctx)
        return TenantComplianceConfigResponse.of(out)

    @router.post(
        "/sync-logs", response_model=NationalSyncLogResponse, status_code=status.HTTP_201_CREATED
    )
    async def push_sync_log(
        body: PushSyncRequest,
        service: NationalSyncService = Depends(_sync_service),
        ctx: RequestContext = Depends(get_context),
    ) -> NationalSyncLogResponse:
        """Đẩy thủ công — luồng chính là tự động qua sự kiện ``SaleCompleted``."""
        out = await service.push_payload(body.to_input(), ctx)
        return NationalSyncLogResponse.of(out)

    @router.get("/sync-logs/{log_id}", response_model=NationalSyncLogResponse)
    async def get_sync_log(
        log_id: UUID,
        service: NationalSyncService = Depends(_sync_service),
        ctx: RequestContext = Depends(get_context),
    ) -> NationalSyncLogResponse:
        out = await service.get_sync_log(log_id, ctx)
        return NationalSyncLogResponse.of(out)

    return router
