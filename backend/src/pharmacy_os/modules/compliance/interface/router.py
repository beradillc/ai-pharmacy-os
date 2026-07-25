"""Compliance HTTP endpoints: sổ thuốc kiểm soát đặc biệt, cấu hình tenant, liên thông CSDL Dược."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.http import csv_stream_body
from pharmacy_os.modules.compliance.application import (
    LEDGER_BOOK_CSV_HEADER,
    PERIODIC_REPORT_CSV_HEADER,
    ComplianceService,
    NationalSyncService,
    ledger_book_row_to_csv,
    periodic_report_row_to_csv,
)
from pharmacy_os.modules.compliance.domain import LedgerBookType
from pharmacy_os.modules.compliance.interface.schemas import (
    ControlledLedgerEntryResponse,
    DrugReturnRecordResponse,
    NationalSyncLogResponse,
    PushSyncRequest,
    RecordControlledEntryRequest,
    RecordDrugReturnRequest,
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

    @router.get("/controlled-ledger/books/{book_type}/export")
    async def export_ledger_book(
        book_type: LedgerBookType,
        date_from: date = Query(..., description="Từ ngày (bao gồm)"),
        date_to: date = Query(..., description="Đến ngày (bao gồm)"),
        drug_id: UUID | None = Query(
            None, description="Lọc 1 thuốc (mẫu sổ pháp lý: mỗi thuốc một sổ riêng)"
        ),
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StreamingResponse:
        """Kết xuất Sổ theo dõi xuất, nhập, tồn kho dạng CSV — TT18 Phụ lục VIII / XVI.

        ``PL_VIII`` cho GN/HT/TC (Điều 12.1.a), ``PL_XVI`` cho thuốc dạng phối hợp, thuốc độc,
        thuốc thuộc danh mục chất bị cấm (Điều 12.3). Dùng lại quyền ``compliance.ledger.read``.

        Bỏ trống ``drug_id`` thì file gộp nhiều thuốc, phân biệt bằng cột ``drug_id`` — mẫu sổ
        pháp lý bắt **mỗi thuốc một sổ riêng**, nên khi in ra để ký phải xuất từng thuốc một.
        """
        rows = await service.ledger_book_rows(
            book_type, from_date=date_from, to_date=date_to, drug_id=drug_id, ctx=ctx
        )

        async def csv_rows() -> AsyncIterator[Sequence[str]]:
            for row in rows:
                yield ledger_book_row_to_csv(row)

        filename = f"so-{book_type.value.lower()}-{ctx.tenant_id}-{date_from}_{date_to}.csv"
        return StreamingResponse(
            csv_stream_body(LEDGER_BOOK_CSV_HEADER, csv_rows()),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @router.get("/periodic-report/export")
    async def export_periodic_report(
        date_from: date = Query(..., description="Từ ngày (bao gồm)"),
        date_to: date = Query(..., description="Đến ngày (bao gồm)"),
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> StreamingResponse:
        """Báo cáo định kỳ Mẫu số 06 dạng CSV — NĐ 163/2025 Điều 35.2.a (docs/13 mục C.7).

        Kỳ 6 tháng (01/01–30/06, nộp trước 15/7) hoặc năm (01/01–31/12, nộp trước 15/01), gửi
        UBND cấp tỉnh. Dùng lại quyền ``compliance.ledger.read``. Mỗi lần gọi ghi 1 dòng audit
        ``PERIODIC_REPORT_EXPORTED`` — bằng chứng "đã tạo báo cáo kỳ này lúc nào, ai tạo" khi
        thanh tra hỏi.

        3 cột không có nguồn dữ liệu trong hệ thống (nước sản xuất, quy cách đóng gói, số công
        văn cho phép mua trong nước) và cột hao hụt luôn để trống trong file — điền tay theo
        thực tế trước khi nộp (xem `docs/features/bao-cao-dinh-ky-nd163/01_DECISIONS.md`).
        """
        rows = await service.export_periodic_report(from_date=date_from, to_date=date_to, ctx=ctx)

        async def csv_rows() -> AsyncIterator[Sequence[str]]:
            for index, row in enumerate(rows, start=1):
                yield periodic_report_row_to_csv(index, row)

        filename = f"bao-cao-mau06-{ctx.tenant_id}-{date_from}_{date_to}.csv"
        return StreamingResponse(
            csv_stream_body(PERIODIC_REPORT_CSV_HEADER, csv_rows()),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Khai báo SAU route "books/..." là cố ý: FastAPI khớp theo thứ tự, để trước thì
    # "books" bị bắt làm ``entry_id`` và request kết xuất sổ trả 422 thay vì file.
    # ("periodic-report/export" ở trên không cần quan tâm thứ tự này — khác hẳn prefix
    # "/controlled-ledger/", không có đường nào khớp nhầm.)
    @router.get("/controlled-ledger/{entry_id}", response_model=ControlledLedgerEntryResponse)
    async def get_ledger_entry(
        entry_id: UUID,
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> ControlledLedgerEntryResponse:
        out = await service.get_ledger_entry(entry_id, ctx)
        return ControlledLedgerEntryResponse.of(out)

    @router.post(
        "/drug-returns",
        response_model=DrugReturnRecordResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def record_drug_return(
        body: RecordDrugReturnRequest,
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> DrugReturnRecordResponse:
        """Biên bản nhận lại thuốc GN/HT/TC (docs/13 mục C.6 — TT18 Điều 6.2 + Điều 12.1.d)."""
        out = await service.record_drug_return(body.to_input(), ctx)
        return DrugReturnRecordResponse.of(out)

    @router.get("/drug-returns/{record_id}", response_model=DrugReturnRecordResponse)
    async def get_drug_return(
        record_id: UUID,
        service: ComplianceService = Depends(_compliance_service),
        ctx: RequestContext = Depends(get_context),
    ) -> DrugReturnRecordResponse:
        out = await service.get_drug_return(record_id, ctx)
        return DrugReturnRecordResponse.of(out)

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
