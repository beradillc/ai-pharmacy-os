"""SQLAlchemy implementation of :class:`SalesRepository`, tenant-scoped."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.sales.domain import SalesOrder
from pharmacy_os.modules.sales.infrastructure.mappers import to_domain, to_orm
from pharmacy_os.modules.sales.infrastructure.models import SalesOrderORM


class SqlAlchemySalesRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, order: SalesOrder) -> None:
        self._session.add(to_orm(order))
        await self._session.flush()

    async def get(self, order_id: UUID) -> SalesOrder | None:
        stmt = select(SalesOrderORM).where(
            SalesOrderORM.id == order_id,
            SalesOrderORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def by_client_uuid(self, client_uuid: str) -> SalesOrder | None:
        stmt = select(SalesOrderORM).where(
            SalesOrderORM.client_uuid == client_uuid,
            SalesOrderORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None
