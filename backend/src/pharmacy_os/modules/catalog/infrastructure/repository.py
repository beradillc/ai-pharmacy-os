"""SQLAlchemy implementation of :class:`DrugRepository`, tenant-scoped."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.catalog.domain import Drug
from pharmacy_os.modules.catalog.infrastructure.mappers import to_domain, to_orm
from pharmacy_os.modules.catalog.infrastructure.models import DrugORM


class SqlAlchemyDrugRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, drug: Drug) -> None:
        self._session.add(to_orm(drug, self._ctx.tenant_id))
        await self._session.flush()

    async def get(self, drug_id: UUID) -> Drug | None:
        stmt = select(DrugORM).where(
            DrugORM.id == drug_id, DrugORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def by_barcode(self, barcode: str) -> Drug | None:
        stmt = select(DrugORM).where(
            DrugORM.barcode == barcode, DrugORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Drug]:
        stmt = (
            select(DrugORM)
            .where(DrugORM.tenant_id == self._ctx.tenant_id)
            .order_by(DrugORM.name)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [to_domain(r) for r in rows]
