"""SQLAlchemy implementations of compliance repository ports, tenant-scoped."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.compliance.domain import (
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    DrugReturnRecord,
    LedgerBookSignature,
    LedgerBookType,
    LedgerDirection,
    LedgerPeriodAggregate,
    NationalSyncLog,
    TenantComplianceConfig,
    book_type_for,
)
from pharmacy_os.modules.compliance.infrastructure.mappers import (
    drug_return_record_to_domain,
    drug_return_record_to_orm,
    ledger_book_signature_to_domain,
    ledger_book_signature_to_orm,
    ledger_entry_to_domain,
    ledger_entry_to_orm,
    sync_log_to_domain,
    sync_log_to_orm,
    tenant_config_to_domain,
    tenant_config_to_orm,
)
from pharmacy_os.modules.compliance.infrastructure.models import (
    ControlledLedgerEntryORM,
    DrugReturnRecordORM,
    LedgerBookSignatureORM,
    NationalSyncLogORM,
    TenantComplianceConfigORM,
)


def _book_of(category: ControlledSubstanceCategory) -> LedgerBookType | None:
    """``book_type_for`` nhưng trả ``None`` thay vì ném cho nhóm NONE (không có sổ)."""
    if category is ControlledSubstanceCategory.NONE:
        return None
    return book_type_for(category)


class SqlAlchemyControlledLedgerRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, entry: ControlledLedgerEntry) -> None:
        self._session.add(ledger_entry_to_orm(entry))
        await self._session.flush()

    async def get(self, entry_id: UUID) -> ControlledLedgerEntry | None:
        stmt = select(ControlledLedgerEntryORM).where(
            ControlledLedgerEntryORM.id == entry_id,
            ControlledLedgerEntryORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return ledger_entry_to_domain(row) if row is not None else None

    async def list_for_book(
        self,
        book_type: LedgerBookType,
        *,
        from_date: date,
        to_date: date,
        drug_id: UUID | None = None,
    ) -> Sequence[ControlledLedgerEntry]:
        """Lọc theo nhóm thuốc của mẫu sổ — ``book_type`` không phải cột, suy từ ``category``.

        Sổ là hồ sơ của **cơ sở** (theo giấy phép), không phải của từng quầy, nên phạm vi là
        tenant — không lọc thêm theo ``branch_id``.
        """
        categories = [c.value for c in ControlledSubstanceCategory if _book_of(c) is book_type]
        stmt = (
            select(ControlledLedgerEntryORM)
            .where(
                ControlledLedgerEntryORM.tenant_id == self._ctx.tenant_id,
                ControlledLedgerEntryORM.category.in_(categories),
                func.date(ControlledLedgerEntryORM.transaction_at) >= from_date,
                func.date(ControlledLedgerEntryORM.transaction_at) <= to_date,
            )
            .order_by(
                ControlledLedgerEntryORM.drug_id,
                ControlledLedgerEntryORM.transaction_at,
                ControlledLedgerEntryORM.id,
            )
        )
        if drug_id is not None:
            stmt = stmt.where(ControlledLedgerEntryORM.drug_id == drug_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [ledger_entry_to_domain(row) for row in rows]

    async def aggregate_for_period(
        self,
        categories: Sequence[ControlledSubstanceCategory],
        *,
        from_date: date,
        to_date: date,
    ) -> Sequence[LedgerPeriodAggregate]:
        """Tổng bằng SQL (SUM/CASE), không load từng dòng lịch sử vào Python.

        ``opening_balance`` cộng dồn MỌI giao dịch trước ``from_date`` (không giới hạn theo
        năm/kỳ nào) — đúng ý nghĩa "tồn kỳ trước chuyển sang" của Mẫu số 06 NĐ163.
        """
        category_values = [c.value for c in categories]
        entry_date = func.date(ControlledLedgerEntryORM.transaction_at)
        is_nhap = ControlledLedgerEntryORM.direction == LedgerDirection.NHAP.value
        is_xuat = ControlledLedgerEntryORM.direction == LedgerDirection.XUAT.value
        in_period = entry_date.between(from_date, to_date)
        opening = func.sum(
            case(
                (
                    entry_date < from_date,
                    case(
                        (is_nhap, ControlledLedgerEntryORM.quantity),
                        else_=-ControlledLedgerEntryORM.quantity,
                    ),
                ),
                else_=0,
            )
        )
        received = func.sum(case((in_period & is_nhap, ControlledLedgerEntryORM.quantity), else_=0))
        issued = func.sum(case((in_period & is_xuat, ControlledLedgerEntryORM.quantity), else_=0))
        stmt = (
            select(
                ControlledLedgerEntryORM.drug_id,
                ControlledLedgerEntryORM.category,
                opening.label("opening"),
                received.label("received"),
                issued.label("issued"),
            )
            .where(
                ControlledLedgerEntryORM.tenant_id == self._ctx.tenant_id,
                ControlledLedgerEntryORM.category.in_(category_values),
                entry_date <= to_date,
            )
            .group_by(ControlledLedgerEntryORM.drug_id, ControlledLedgerEntryORM.category)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            LedgerPeriodAggregate(
                drug_id=row.drug_id,
                category=ControlledSubstanceCategory(row.category),
                opening_balance=Decimal(row.opening or 0),
                received_in_period=Decimal(row.received or 0),
                issued_in_period=Decimal(row.issued or 0),
            )
            for row in rows
        ]


class SqlAlchemyTenantComplianceConfigRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def upsert(self, config: TenantComplianceConfig) -> None:
        stmt = select(TenantComplianceConfigORM).where(
            TenantComplianceConfigORM.tenant_id == config.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            self._session.add(tenant_config_to_orm(config))
        else:
            row.ma_co_so_ban_le = config.ma_co_so_ban_le
            row.ma_co_so_ban_buon = config.ma_co_so_ban_buon
        await self._session.flush()

    async def get(self, tenant_id: UUID) -> TenantComplianceConfig | None:
        stmt = select(TenantComplianceConfigORM).where(
            TenantComplianceConfigORM.tenant_id == tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return tenant_config_to_domain(row) if row is not None else None


class SqlAlchemyNationalSyncLogRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, log: NationalSyncLog) -> None:
        self._session.add(sync_log_to_orm(log))
        await self._session.flush()

    async def update(self, log: NationalSyncLog) -> None:
        stmt = select(NationalSyncLogORM).where(
            NationalSyncLogORM.id == log.id,
            NationalSyncLogORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.status = log.status.value
        row.request_at = log.request_at
        row.response_at = log.response_at
        row.response_code = log.response_code
        row.response_body = log.response_body
        row.retry_count = log.retry_count
        row.error = log.error
        await self._session.flush()

    async def get(self, log_id: UUID) -> NationalSyncLog | None:
        stmt = select(NationalSyncLogORM).where(
            NationalSyncLogORM.id == log_id,
            NationalSyncLogORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return sync_log_to_domain(row) if row is not None else None

    async def by_client_uuid(self, client_uuid: str) -> NationalSyncLog | None:
        stmt = select(NationalSyncLogORM).where(
            NationalSyncLogORM.client_uuid == client_uuid,
            NationalSyncLogORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return sync_log_to_domain(row) if row is not None else None


class SqlAlchemyLedgerBookSignatureRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, signature: LedgerBookSignature) -> None:
        self._session.add(ledger_book_signature_to_orm(signature))
        await self._session.flush()

    async def get_for_day(
        self, book_type: LedgerBookType, book_date: date
    ) -> LedgerBookSignature | None:
        stmt = select(LedgerBookSignatureORM).where(
            LedgerBookSignatureORM.tenant_id == self._ctx.tenant_id,
            LedgerBookSignatureORM.book_type == book_type.value,
            LedgerBookSignatureORM.book_date == book_date,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return ledger_book_signature_to_domain(row) if row is not None else None

    async def latest_before(
        self, book_type: LedgerBookType, book_date: date
    ) -> LedgerBookSignature | None:
        stmt = (
            select(LedgerBookSignatureORM)
            .where(
                LedgerBookSignatureORM.tenant_id == self._ctx.tenant_id,
                LedgerBookSignatureORM.book_type == book_type.value,
                LedgerBookSignatureORM.book_date < book_date,
            )
            .order_by(LedgerBookSignatureORM.book_date.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return ledger_book_signature_to_domain(row) if row is not None else None


class SqlAlchemyDrugReturnRecordRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, record: DrugReturnRecord) -> None:
        self._session.add(drug_return_record_to_orm(record))
        await self._session.flush()

    async def get(self, record_id: UUID) -> DrugReturnRecord | None:
        stmt = select(DrugReturnRecordORM).where(
            DrugReturnRecordORM.id == record_id,
            DrugReturnRecordORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return drug_return_record_to_domain(row) if row is not None else None
