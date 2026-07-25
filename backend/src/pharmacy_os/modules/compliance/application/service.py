"""Compliance use-cases: record controlled-substance ledger entries, manage tenant config.

The service depends only on ports; concrete repositories and the unit of work are injected
as factories at composition time (see the module ``register``).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import date
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.compliance.application.csv_export import (
    render_ledger_book_csv_text,
    to_book_rows,
    to_periodic_report_rows,
)
from pharmacy_os.modules.compliance.application.dto import (
    ControlledLedgerEntryOutput,
    DailyLedgerClosureExport,
    DrugReturnRecordOutput,
    LedgerBookRow,
    PeriodicReportRow,
    RecordControlledEntryInput,
    RecordDrugReturnInput,
    SetTenantComplianceConfigInput,
    TenantComplianceConfigOutput,
)
from pharmacy_os.modules.compliance.domain import (
    ComplianceError,
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    CustomerDetail,
    DrugReturnRecord,
    LedgerBookType,
    LedgerDirection,
    ReturnedDrugItem,
    TenantComplianceConfig,
    validate_controlled_sale,
)
from pharmacy_os.modules.compliance.domain.ports import (
    ControlledLedgerRepository,
    DrugMasterFacts,
    DrugMasterProvider,
    DrugReturnRecordRepository,
    TenantComplianceConfigRepository,
)

UowFactory = Callable[[], UnitOfWork]
LedgerRepoFactory = Callable[[UnitOfWork, RequestContext], ControlledLedgerRepository]
ConfigRepoFactory = Callable[[UnitOfWork, RequestContext], TenantComplianceConfigRepository]
DrugReturnRepoFactory = Callable[[UnitOfWork, RequestContext], DrugReturnRecordRepository]

#: Phạm vi NĐ163 Điều 35.2.a — không gồm THUOC_DOC/DANH_MUC_CAM (Điều 35.2.b chỉ bắt bán lẻ
#: báo cáo phóng xạ, không bắt 2 nhóm đó; cũng không gồm NONE — thuốc không kiểm soát).
_PERIODIC_REPORT_CATEGORIES = (
    ControlledSubstanceCategory.GAY_NGHIEN,
    ControlledSubstanceCategory.HUONG_THAN,
    ControlledSubstanceCategory.TIEN_CHAT,
    ControlledSubstanceCategory.PHOI_HOP_GN,
    ControlledSubstanceCategory.PHOI_HOP_HT,
    ControlledSubstanceCategory.PHOI_HOP_TC,
)


class ComplianceService:
    def __init__(
        self,
        uow_factory: UowFactory,
        ledger_repo_factory: LedgerRepoFactory,
        config_repo_factory: ConfigRepoFactory,
        audit: AuditLogger,
        drug_master: DrugMasterProvider | None = None,
        drug_return_repo_factory: DrugReturnRepoFactory | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._ledger_repo_factory = ledger_repo_factory
        self._config_repo_factory = config_repo_factory
        self._audit = audit
        self._drug_master = drug_master
        self._drug_return_repo_factory = drug_return_repo_factory

    async def record_controlled_entry(
        self, data: RecordControlledEntryInput, ctx: RequestContext
    ) -> ControlledLedgerEntryOutput:
        """Ghi 1 dòng Sổ thuốc kiểm soát đặc biệt (docs/13 mục C.2.1).

        Chiều ``XUAT`` (bán ra) phải qua rule C.3 (:func:`validate_controlled_sale`) trước khi
        ghi sổ — chiều ``NHAP`` (nhập kho) không áp dụng khái niệm khách hàng/đơn thuốc.
        """
        require_permission(ctx, "compliance.ledger.write")

        customer = (
            CustomerDetail(
                patient_name=data.customer.patient_name,
                patient_address=data.customer.patient_address,
            )
            if data.customer is not None
            else None
        )

        if data.direction is LedgerDirection.XUAT:
            try:
                validate_controlled_sale(
                    data.category,
                    prescription_code=data.prescription_code,
                    customer=customer,
                )
            except ComplianceError as exc:
                raise ValidationError(str(exc)) from exc

        try:
            entry = ControlledLedgerEntry(
                tenant_id=ctx.tenant_id,
                branch_id=ctx.branch_id,
                drug_id=data.drug_id,
                category=data.category,
                direction=data.direction,
                quantity=data.quantity,
                lot_no=data.lot_no,
                expiry_date=data.expiry_date,
                transaction_at=data.transaction_at,
                source_or_destination=data.source_or_destination,
                document_no=data.document_no,
                prescription_code=data.prescription_code,
                customer=customer,
                note=data.note,
            )
        except (ComplianceError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._ledger_repo_factory(uow, ctx)
            await repo.add(entry)
            await uow.commit()

        await self._record(
            ctx, AuditAction.CONTROLLED_LEDGER_ENTRY_RECORDED, "controlled_ledger_entry", entry.id
        )
        return ControlledLedgerEntryOutput.of(entry)

    async def get_ledger_entry(
        self, entry_id: UUID, ctx: RequestContext
    ) -> ControlledLedgerEntryOutput:
        """Trả về 1 dòng sổ theo id, đã tenant-scope; 404 nếu không có."""
        require_permission(ctx, "compliance.ledger.read")
        async with self._uow_factory() as uow:
            repo = self._ledger_repo_factory(uow, ctx)
            entry = await repo.get(entry_id)
        if entry is None:
            raise NotFoundError(f"Không tìm thấy dòng sổ kiểm soát đặc biệt {entry_id}")
        return ControlledLedgerEntryOutput.of(entry)

    async def ledger_book_rows(
        self,
        book_type: LedgerBookType,
        *,
        from_date: date,
        to_date: date,
        drug_id: UUID | None = None,
        ctx: RequestContext,
    ) -> list[LedgerBookRow]:
        """Các dòng của một mẫu sổ trong kỳ, đã tính sẵn cột "Còn lại" (tồn lũy kế).

        ``PL_VIII`` = GN/HT/TC (TT18 Điều 12.1.a); ``PL_XVI`` = thuốc dạng phối hợp, thuốc
        độc, thuốc thuộc danh mục chất bị cấm (Điều 12.3).
        """
        require_permission(ctx, "compliance.ledger.read")
        if from_date > to_date:
            raise ValidationError("from_date không được sau to_date")
        async with self._uow_factory() as uow:
            repo = self._ledger_repo_factory(uow, ctx)
            entries = await repo.list_for_book(
                book_type, from_date=from_date, to_date=to_date, drug_id=drug_id
            )
        return list(to_book_rows(entries))

    async def export_daily_closure(
        self, book_type: LedgerBookType, *, day: date, ctx: RequestContext
    ) -> DailyLedgerClosureExport:
        """Kết xuất cuối ngày (docs/13 mục C.5 — ghi chú Phụ lục VIII: "trích xuất, in cuối
        mỗi ngày"). Chỉ đáp ứng điều kiện **(a)** của Điều 15.1 (toàn vẹn, có hash) — điều
        kiện **(d)** (chữ ký số/xác nhận điện tử) là bước 6 riêng, chưa code, chờ Chain chọn
        hướng. Cho tới lúc đó, nhà thuốc vẫn phải in file này ra và **ký tay** mỗi ngày.
        """
        require_permission(ctx, "compliance.ledger.read")
        async with self._uow_factory() as uow:
            repo = self._ledger_repo_factory(uow, ctx)
            entries = await repo.list_for_book(book_type, from_date=day, to_date=day)
        rows = list(to_book_rows(entries))
        content = render_ledger_book_csv_text(rows)
        content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()

        await self._audit.record(
            AuditEntry(
                tenant_id=ctx.tenant_id,
                actor_user_id=ctx.user_id,
                action=AuditAction.LEDGER_DAILY_CLOSURE_EXPORTED,
                target_type="ledger_daily_closure",
                target_id=f"{book_type.value}_{day.isoformat()}",
            ).with_context(
                client_ip=ctx.client_ip,
                branch_id=str(ctx.branch_id),
                content_sha256=content_sha256,
            )
        )
        return DailyLedgerClosureExport(
            book_type=book_type.value,
            day=day,
            content=content,
            content_sha256=content_sha256,
            row_count=len(rows),
        )

    async def export_periodic_report(
        self, *, from_date: date, to_date: date, ctx: RequestContext
    ) -> list[PeriodicReportRow]:
        """Báo cáo định kỳ Mẫu số 06 (docs/13 mục C.7 — NĐ163 Điều 35.2.a).

        Phạm vi thuốc: GN/HT/TC + 3 nhóm dạng phối hợp — **không gồm** thuốc độc/danh mục cấm
        (Điều 35.2.b chỉ bắt bán lẻ báo cáo phóng xạ, không bắt báo cáo 2 nhóm đó; BeraLLC cũng
        không kinh doanh 2 nhóm này). Cố ý tách khỏi ``LedgerBookType`` — xem
        :meth:`ControlledLedgerRepository.aggregate_for_period`.
        """
        require_permission(ctx, "compliance.ledger.read")
        if from_date > to_date:
            raise ValidationError("from_date không được sau to_date")
        async with self._uow_factory() as uow:
            repo = self._ledger_repo_factory(uow, ctx)
            aggregates = await repo.aggregate_for_period(
                _PERIODIC_REPORT_CATEGORIES, from_date=from_date, to_date=to_date
            )
        drug_facts: dict[UUID, DrugMasterFacts] = {}
        if self._drug_master is not None:
            for agg in aggregates:
                facts = await self._drug_master.get(agg.drug_id, ctx.tenant_id)
                if facts is not None:
                    drug_facts[agg.drug_id] = facts
        rows = to_periodic_report_rows(aggregates, drug_facts)

        await self._audit.record(
            AuditEntry(
                tenant_id=ctx.tenant_id,
                actor_user_id=ctx.user_id,
                action=AuditAction.PERIODIC_REPORT_EXPORTED,
                target_type="periodic_report",
                target_id=f"{from_date.isoformat()}_{to_date.isoformat()}",
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )
        return rows

    def _drug_return_repo(self, uow: UnitOfWork, ctx: RequestContext) -> DrugReturnRecordRepository:
        if self._drug_return_repo_factory is None:
            raise RuntimeError(
                "ComplianceService chưa được wiring drug_return_repo_factory — lỗi cấu hình, "
                "không phải lỗi người dùng (xem interface/register.py)"
            )
        return self._drug_return_repo_factory(uow, ctx)

    async def record_drug_return(
        self, data: RecordDrugReturnInput, ctx: RequestContext
    ) -> DrugReturnRecordOutput:
        """Ghi biên bản nhận lại thuốc GN/HT/TC (docs/13 mục C.6 — TT18 Điều 6.2 + Điều 12.1.d).

        Không kiểm tra chéo `drug_id`/tồn kho — mẫu Phụ lục XVIII gốc không có cột đó (xem
        docs/features/bien-ban-nhan-lai-pl-xviii/01_DECISIONS.md). Số CCCD/hộ chiếu của người
        giao **không** được đưa vào audit context, cùng nguyên tắc PII đã áp cho tên/địa chỉ
        khách hàng ở :meth:`record_controlled_entry`.
        """
        require_permission(ctx, "compliance.ledger.write")
        try:
            record = DrugReturnRecord(
                tenant_id=ctx.tenant_id,
                branch_id=ctx.branch_id,
                returner_name=data.returner_name,
                returner_address=data.returner_address,
                returner_id_number=data.returner_id_number,
                returner_id_issuer=data.returner_id_issuer,
                returner_id_issued_at=data.returner_id_issued_at,
                returner_is_patient=data.returner_is_patient,
                receiving_pharmacist_name=data.receiving_pharmacist_name,
                items=[
                    ReturnedDrugItem(
                        description=i.description,
                        unit=i.unit,
                        quantity=i.quantity,
                        lot_no=i.lot_no,
                        expiry_date=i.expiry_date,
                        condition_note=i.condition_note,
                        reason=i.reason,
                    )
                    for i in data.items
                ],
                handover_at=data.handover_at,
                handover_location=data.handover_location,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._drug_return_repo(uow, ctx)
            await repo.add(record)
            await uow.commit()

        await self._record(ctx, AuditAction.DRUG_RETURN_RECORDED, "drug_return_record", record.id)
        return DrugReturnRecordOutput.of(record)

    async def get_drug_return(self, record_id: UUID, ctx: RequestContext) -> DrugReturnRecordOutput:
        """Trả về 1 biên bản nhận lại thuốc theo id, đã tenant-scope; 404 nếu không có."""
        require_permission(ctx, "compliance.ledger.read")
        async with self._uow_factory() as uow:
            repo = self._drug_return_repo(uow, ctx)
            record = await repo.get(record_id)
        if record is None:
            raise NotFoundError(f"Không tìm thấy biên bản nhận lại thuốc {record_id}")
        return DrugReturnRecordOutput.of(record)

    async def set_tenant_config(
        self, data: SetTenantComplianceConfigInput, ctx: RequestContext
    ) -> TenantComplianceConfigOutput:
        """Tạo/cập nhật mã cơ sở do Cục QLD cấp cho tenant hiện tại (docs/13 mục F)."""
        require_permission(ctx, "compliance.config.write")
        try:
            config = TenantComplianceConfig(
                tenant_id=ctx.tenant_id,
                ma_co_so_ban_le=data.ma_co_so_ban_le,
                ma_co_so_ban_buon=data.ma_co_so_ban_buon,
            )
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._config_repo_factory(uow, ctx)
            existing = await repo.get(ctx.tenant_id)
            if existing is not None:
                config.id = existing.id
            await repo.upsert(config)
            await uow.commit()

        await self._record(
            ctx, AuditAction.TENANT_COMPLIANCE_CONFIG_SET, "tenant_compliance_config", ctx.tenant_id
        )
        return TenantComplianceConfigOutput.of(config)

    async def get_tenant_config(self, ctx: RequestContext) -> TenantComplianceConfigOutput:
        """Trả về cấu hình tenant hiện tại; 404 nếu chưa cấu hình."""
        require_permission(ctx, "compliance.config.read")
        async with self._uow_factory() as uow:
            repo = self._config_repo_factory(uow, ctx)
            config = await repo.get(ctx.tenant_id)
        if config is None:
            raise NotFoundError(f"Chưa cấu hình mã cơ sở cho tenant {ctx.tenant_id}")
        return TenantComplianceConfigOutput.of(config)

    async def _record(
        self, ctx: RequestContext, action: AuditAction, target_type: str, target_id: UUID
    ) -> None:
        """Append one audit row — metadata only, never patient name/address content."""
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type=target_type,
                target_id=str(target_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )
