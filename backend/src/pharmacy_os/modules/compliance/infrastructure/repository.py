"""SQLAlchemy implementations of compliance repository ports, tenant-scoped."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.compliance.domain import ControlledLedgerEntry, TenantComplianceConfig
from pharmacy_os.modules.compliance.infrastructure.mappers import (
    ledger_entry_to_domain,
    ledger_entry_to_orm,
    tenant_config_to_domain,
    tenant_config_to_orm,
)
from pharmacy_os.modules.compliance.infrastructure.models import (
    ControlledLedgerEntryORM,
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
