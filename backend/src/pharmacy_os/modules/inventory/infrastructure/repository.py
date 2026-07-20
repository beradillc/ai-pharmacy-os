"""SQLAlchemy inventory repositories, tenant/branch-scoped."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.inventory.domain.entities import ProductBatch, StockMovement
from pharmacy_os.modules.inventory.domain.fefo import BatchAvailability
from pharmacy_os.modules.inventory.infrastructure.models import (
    ProductBatchORM,
    StockBalanceORM,
    StockMovementORM,
)


class SqlAlchemyBatchRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, batch: ProductBatch) -> None:
        self._session.add(
            ProductBatchORM(
                id=batch.id,
                tenant_id=batch.tenant_id,
                branch_id=batch.branch_id,
                drug_id=batch.drug_id,
                lot_no=batch.lot_no,
                expiry_date=batch.expiry_date,
                mfg_date=batch.mfg_date,
                cost_price=batch.cost_price,
                quantity_received=batch.quantity_received,
            )
        )
        await self._session.flush()

    async def get(self, batch_id: UUID) -> ProductBatch | None:
        stmt = select(ProductBatchORM).where(
            ProductBatchORM.id == batch_id,
            ProductBatchORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _batch_to_domain(row) if row is not None else None

    async def availabilities(
        self, drug_id: UUID, branch_id: UUID, *, not_expired_on: date
    ) -> list[BatchAvailability]:
        stmt = (
            select(
                ProductBatchORM.id,
                ProductBatchORM.expiry_date,
                StockBalanceORM.quantity,
            )
            .join(StockBalanceORM, StockBalanceORM.batch_id == ProductBatchORM.id)
            .where(
                ProductBatchORM.drug_id == drug_id,
                ProductBatchORM.branch_id == branch_id,
                ProductBatchORM.tenant_id == self._ctx.tenant_id,
                ProductBatchORM.expiry_date >= not_expired_on,
                StockBalanceORM.quantity > 0,
            )
        )
        rows = (await self._session.execute(stmt)).all()
        return [BatchAvailability(batch_id=r[0], expiry_date=r[1], available=r[2]) for r in rows]

    async def near_expiry(self, branch_id: UUID, *, before: date) -> list[ProductBatch]:
        stmt = (
            select(ProductBatchORM)
            .where(
                ProductBatchORM.branch_id == branch_id,
                ProductBatchORM.tenant_id == self._ctx.tenant_id,
                ProductBatchORM.expiry_date <= before,
            )
            .order_by(ProductBatchORM.expiry_date)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_batch_to_domain(r) for r in rows]


class SqlAlchemyMovementRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, movement: StockMovement) -> None:
        self._session.add(
            StockMovementORM(
                id=movement.id,
                tenant_id=movement.tenant_id,
                branch_id=movement.branch_id,
                drug_id=movement.drug_id,
                batch_id=movement.batch_id,
                type=movement.type.value,
                quantity=movement.quantity,
                ref_type=movement.ref_type,
                ref_id=movement.ref_id,
                occurred_at=movement.occurred_at,
            )
        )
        await self._session.flush()


class SqlAlchemyBalanceRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def adjust(
        self, drug_id: UUID, batch_id: UUID, branch_id: UUID, tenant_id: UUID, delta: Decimal
    ) -> Decimal:
        stmt = select(StockBalanceORM).where(
            StockBalanceORM.drug_id == drug_id,
            StockBalanceORM.batch_id == batch_id,
            StockBalanceORM.branch_id == branch_id,
            StockBalanceORM.tenant_id == tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = StockBalanceORM(
                tenant_id=tenant_id,
                branch_id=branch_id,
                drug_id=drug_id,
                batch_id=batch_id,
                quantity=delta,
            )
            self._session.add(row)
        else:
            row.quantity = row.quantity + delta
        await self._session.flush()
        return row.quantity

    async def on_hand(self, drug_id: UUID, branch_id: UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(StockBalanceORM.quantity), 0)).where(
            StockBalanceORM.drug_id == drug_id,
            StockBalanceORM.branch_id == branch_id,
            StockBalanceORM.tenant_id == self._ctx.tenant_id,
        )
        total = (await self._session.execute(stmt)).scalar_one()
        return Decimal(total)


def _batch_to_domain(row: ProductBatchORM) -> ProductBatch:
    return ProductBatch(
        id=row.id,
        drug_id=row.drug_id,
        branch_id=row.branch_id,
        tenant_id=row.tenant_id,
        lot_no=row.lot_no,
        expiry_date=row.expiry_date,
        mfg_date=row.mfg_date,
        cost_price=row.cost_price,
        quantity_received=row.quantity_received,
    )
