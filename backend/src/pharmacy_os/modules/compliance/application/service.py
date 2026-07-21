"""Compliance use-cases: record controlled-substance ledger entries, manage tenant config.

The service depends only on ports; concrete repositories and the unit of work are injected
as factories at composition time (see the module ``register``).
"""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.compliance.application.dto import (
    ControlledLedgerEntryOutput,
    RecordControlledEntryInput,
    SetTenantComplianceConfigInput,
    TenantComplianceConfigOutput,
)
from pharmacy_os.modules.compliance.domain import (
    ComplianceError,
    ControlledLedgerEntry,
    CustomerDetail,
    LedgerDirection,
    TenantComplianceConfig,
    validate_controlled_sale,
)
from pharmacy_os.modules.compliance.domain.ports import (
    ControlledLedgerRepository,
    TenantComplianceConfigRepository,
)

UowFactory = Callable[[], UnitOfWork]
LedgerRepoFactory = Callable[[UnitOfWork, RequestContext], ControlledLedgerRepository]
ConfigRepoFactory = Callable[[UnitOfWork, RequestContext], TenantComplianceConfigRepository]


class ComplianceService:
    def __init__(
        self,
        uow_factory: UowFactory,
        ledger_repo_factory: LedgerRepoFactory,
        config_repo_factory: ConfigRepoFactory,
    ) -> None:
        self._uow_factory = uow_factory
        self._ledger_repo_factory = ledger_repo_factory
        self._config_repo_factory = config_repo_factory

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
