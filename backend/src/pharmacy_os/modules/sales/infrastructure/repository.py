"""SQLAlchemy implementation of :class:`SalesRepository`, tenant-scoped."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.sales.domain import SalesOrder, SaleStatus
from pharmacy_os.modules.sales.domain.ports import (
    DrugSalesAggRow,
    OrderRevenueRow,
    SalesOrderListRow,
)
from pharmacy_os.modules.sales.infrastructure.mappers import to_domain, to_orm
from pharmacy_os.modules.sales.infrastructure.models import (
    PaymentORM,
    SaleLineORM,
    SalesOrderORM,
)

#: Độ rộng mọi cột tiền trong hệ thống. Đặt tên để hai chỗ dùng không trôi khỏi nhau.
_MONEY = Decimal("0.01")


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
        existing_payment_ids = {p.id for p in row.payments}
        for payment in order.payments:
            if payment.id in existing_payment_ids:
                continue
            row.payments.append(
                PaymentORM(
                    id=payment.id,
                    order_id=order.id,
                    method=payment.method.value,
                    amount=payment.amount.amount,
                    gateway_ref=payment.gateway_ref,
                )
            )
        await self._session.flush()

    async def get(self, order_id: UUID) -> SalesOrder | None:
        stmt = select(SalesOrderORM).where(
            SalesOrderORM.id == order_id,
            SalesOrderORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_domain(row) if row is not None else None

    async def get_across_tenants(self, order_id: UUID) -> SalesOrder | None:
        stmt = select(SalesOrderORM).where(SalesOrderORM.id == order_id)
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

    async def list_orders(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        created_from: datetime,
        created_to: datetime,
        limit: int,
        offset: int,
    ) -> list[SalesOrderListRow]:
        """Till list of orders, newest first — drafts included (see the port docstring).

        Lines and payments are aggregated in **separate subqueries** rather than two
        joins off the order: joining both at once multiplies rows (lines × payments),
        which would silently inflate both ``subtotal`` and ``paid_total`` on any order
        settled with more than one tender. ``COALESCE`` covers the two legitimate
        empty sides — a draft with no payment yet, and (defensively) an order with no
        lines.
        """
        lines = (
            select(
                SaleLineORM.order_id.label("order_id"),
                func.sum(SaleLineORM.quantity * SaleLineORM.unit_price).label("subtotal"),
                func.count(SaleLineORM.id).label("line_count"),
            )
            .group_by(SaleLineORM.order_id)
            .subquery()
        )
        payments = (
            select(
                PaymentORM.order_id.label("order_id"),
                func.sum(PaymentORM.amount).label("paid_total"),
            )
            .group_by(PaymentORM.order_id)
            .subquery()
        )
        stmt = (
            select(
                SalesOrderORM.id,
                SalesOrderORM.branch_id,
                SalesOrderORM.created_at,
                SalesOrderORM.status,
                SalesOrderORM.currency,
                SalesOrderORM.customer_id,
                SalesOrderORM.sold_by_user_id,
                func.coalesce(lines.c.subtotal, 0).label("subtotal"),
                func.coalesce(lines.c.line_count, 0).label("line_count"),
                func.coalesce(payments.c.paid_total, 0).label("paid_total"),
            )
            .outerjoin(lines, lines.c.order_id == SalesOrderORM.id)
            .outerjoin(payments, payments.c.order_id == SalesOrderORM.id)
            .where(
                SalesOrderORM.tenant_id == tenant_id,
                SalesOrderORM.created_at >= created_from,
                SalesOrderORM.created_at < created_to,
            )
        )
        if branch_id is not None:
            stmt = stmt.where(SalesOrderORM.branch_id == branch_id)
        stmt = (
            stmt.order_by(SalesOrderORM.created_at.desc(), SalesOrderORM.id.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            SalesOrderListRow(
                order_id=r.id,
                branch_id=r.branch_id,
                created_at=r.created_at,
                status=r.status,
                currency=r.currency,
                # Lượng Numeric(18,3) × giá Numeric(18,2) ⇒ 5 chữ số thập phân
                # ("19400.00000"), một hình dạng tiền không có ở cột nào khác. Quy
                # về 2 chữ số ngay tại đây, cùng quy ước với PurchaseOrderListItem.
                subtotal=Decimal(r.subtotal).quantize(_MONEY, rounding=ROUND_HALF_UP),
                paid_total=Decimal(r.paid_total).quantize(_MONEY, rounding=ROUND_HALF_UP),
                line_count=r.line_count,
                customer_id=r.customer_id,
                sold_by_user_id=r.sold_by_user_id,
            )
            for r in rows
        ]

    async def accrued_by_customer(
        self,
        tenant_id: UUID,
        customer_ids: Sequence[UUID],
        *,
        created_from: datetime,
        created_to: datetime,
    ) -> dict[UUID, Decimal]:
        if not customer_ids:
            # `IN ()` là lỗi cú pháp ở nền này và quét toàn bảng ở nền kia — cùng lý do
            # với `names_by_ids` bên catalog.
            return {}
        net_qty = SaleLineORM.quantity - SaleLineORM.returned_quantity
        stmt = (
            select(
                SalesOrderORM.customer_id,
                func.sum(net_qty * SaleLineORM.unit_price).label("accrued"),
            )
            .join(SaleLineORM, SaleLineORM.order_id == SalesOrderORM.id)
            .where(
                SalesOrderORM.tenant_id == tenant_id,
                SalesOrderORM.customer_id.in_(customer_ids),
                # Cùng bộ lọc với `aggregate_sold_by_drug`: đơn nháp chưa phải doanh thu.
                SalesOrderORM.status != SaleStatus.DRAFT.value,
                SalesOrderORM.created_at >= created_from,
                SalesOrderORM.created_at < created_to,
            )
            .group_by(SalesOrderORM.customer_id)
        )
        rows = (await self._session.execute(stmt)).all()
        return {r.customer_id: Decimal(r.accrued or 0) for r in rows if r.customer_id}

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
