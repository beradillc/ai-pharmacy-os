"""SQLAlchemy implementations of compliance repository ports, tenant-scoped."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.compliance.domain import (
    ControlledLedgerEntry,
    NationalSyncLog,
    TenantComplianceConfig,
)
from pharmacy_os.modules.compliance.infrastructure.mappers import (
    ledger_entry_to_domain,
    ledger_entry_to_orm,
    sync_log_to_domain,
    sync_log_to_orm,
    tenant_config_to_domain,
    tenant_config_to_orm,
)
from pharmacy_os.modules.compliance.infrastructure.models import (
    ControlledLedgerEntryORM,
    NationalSyncLogORM,
    TenantComplianceConfigORM,
)


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
