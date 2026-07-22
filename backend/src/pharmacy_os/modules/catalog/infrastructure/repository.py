"""SQLAlchemy implementation of :class:`DrugRepository`, tenant-scoped."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.catalog.domain import ActiveIngredient, Drug
from pharmacy_os.modules.catalog.infrastructure.mappers import (
    ingredient_to_domain,
    ingredient_to_orm,
    to_domain,
    to_orm,
)
from pharmacy_os.modules.catalog.infrastructure.models import ActiveIngredientORM, DrugORM


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


class SqlAlchemyActiveIngredientRepository:
    """Global (not tenant-scoped) access to ``active_ingredients``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, ingredient: ActiveIngredient) -> None:
        self._session.add(ingredient_to_orm(ingredient))
        await self._session.flush()

    async def get(self, ingredient_id: UUID) -> ActiveIngredient | None:
        row = await self._session.get(ActiveIngredientORM, ingredient_id)
        return ingredient_to_domain(row) if row is not None else None

    async def find_by_name(self, name: str) -> ActiveIngredient | None:
        stmt = select(ActiveIngredientORM).where(ActiveIngredientORM.name == name)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return ingredient_to_domain(row) if row is not None else None

    async def list(self) -> list[ActiveIngredient]:
        stmt = select(ActiveIngredientORM).order_by(ActiveIngredientORM.name)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [ingredient_to_domain(r) for r in rows]
