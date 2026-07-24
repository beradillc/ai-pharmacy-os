"""SQLAlchemy implementation of :class:`SalesRepository`, tenant-scoped."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.sales.domain import SalesOrder, SaleStatus
from pharmacy_os.modules.sales.domain.ports import DrugSalesAggRow, OrderRevenueRow
from pharmacy_os.modules.sales.infrastructure.mappers import to_domain, to_orm
from pharmacy_os.modules.sales.infrastructure.models import SaleLineORM, SalesOrderORM


class SqlAlchemySalesRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, order: SalesOrder) -> None:
        self._session.add(to_orm(order))
        await self._session.flush()

    async def update(self, order: SalesOrder) -> None:
        stmt = select(SalesOrderORM).where(
            SalesOrderORM.id == order.id,
            SalesOrderORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.status = order.status.value
        lines_by_id = {ln.id: ln for ln in row.lines}
        for line in order.lines:
            lines_by_id[line.id].returned_quantity = line.returned_quantity
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

    async def completed_in_range(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        sold_by_user_id: UUID | None,
        created_from: datetime,
        created_to: datetime,
        limit: int,
        offset: int,
    ) -> list[OrderRevenueRow]:
        """Order-level revenue (SUM over its lines), oldest first.

        ``status != DRAFT`` is the "completed" test: a draft never reached
        ``complete()`` (Rx + full-payment checks), so it carries no committed
        revenue — see ``SalesOrder.complete``. A returned/partially-returned order
        still counts at its original (gross) amount: the report shows revenue as
        recognised at sale time, not netted against later returns (documented gap,
        PROJECT_STATE §7an).
        """
        stmt = (
            select(
                SalesOrderORM.id,
                SalesOrderORM.branch_id,
                SalesOrderORM.currency,
                SalesOrderORM.created_at,
                SalesOrderORM.sold_by_user_id,
                func.sum(SaleLineORM.quantity * SaleLineORM.unit_price).label("subtotal"),
            )
            .join(SaleLineORM, SaleLineORM.order_id == SalesOrderORM.id)
            .where(
                SalesOrderORM.tenant_id == tenant_id,
                SalesOrderORM.status != SaleStatus.DRAFT.value,
                SalesOrderORM.created_at >= created_from,
                SalesOrderORM.created_at < created_to,
            )
        )
        if branch_id is not None:
            stmt = stmt.where(SalesOrderORM.branch_id == branch_id)
        if sold_by_user_id is not None:
            stmt = stmt.where(SalesOrderORM.sold_by_user_id == sold_by_user_id)
        stmt = (
            stmt.group_by(
                SalesOrderORM.id,
                SalesOrderORM.branch_id,
                SalesOrderORM.currency,
                SalesOrderORM.created_at,
                SalesOrderORM.sold_by_user_id,
            )
            .order_by(SalesOrderORM.created_at, SalesOrderORM.id)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            OrderRevenueRow(
                order_id=r.id,
                branch_id=r.branch_id,
                currency=r.currency,
                created_at=r.created_at,
                subtotal=r.subtotal,
                sold_by_user_id=r.sold_by_user_id,
            )
            for r in rows
        ]

    async def aggregate_sold_by_drug(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        created_from: datetime,
        created_to: datetime,
    ) -> list[DrugSalesAggRow]:
        net_qty = SaleLineORM.quantity - SaleLineORM.returned_quantity
        stmt = (
            select(
                SaleLineORM.drug_id,
                SalesOrderORM.branch_id,
                func.sum(net_qty).label("quantity_sold"),
                func.sum(net_qty * SaleLineORM.unit_price).label("revenue"),
            )
            .join(SalesOrderORM, SaleLineORM.order_id == SalesOrderORM.id)
            .where(
                SalesOrderORM.tenant_id == tenant_id,
                SalesOrderORM.status != SaleStatus.DRAFT.value,
                SalesOrderORM.created_at >= created_from,
                SalesOrderORM.created_at < created_to,
            )
        )
        if branch_id is not None:
            stmt = stmt.where(SalesOrderORM.branch_id == branch_id)
        stmt = stmt.group_by(SaleLineORM.drug_id, SalesOrderORM.branch_id).having(
            func.sum(net_qty) > 0
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            DrugSalesAggRow(
                drug_id=r.drug_id,
                branch_id=r.branch_id,
                quantity_sold=r.quantity_sold,
                revenue=r.revenue,
            )
            for r in rows
        ]
