"""SQLAlchemy inventory repositories, tenant/branch-scoped."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.inventory.domain.entities import (
    ProductBatch,
    StockMovement,
    StockReconciliationNeeded,
)
from pharmacy_os.modules.inventory.domain.exceptions import InsufficientStockError
from pharmacy_os.modules.inventory.domain.fefo import BatchAvailability
from pharmacy_os.modules.inventory.domain.ports import BatchStockRow, DrugOnHandRow
from pharmacy_os.modules.inventory.infrastructure.models import (
    ProductBatchORM,
    StockBalanceORM,
    StockMovementORM,
    StockReconciliationNeededORM,
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

    async def update(self, batch: ProductBatch) -> None:
        stmt = select(ProductBatchORM).where(
            ProductBatchORM.id == batch.id,
            ProductBatchORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.quantity_received = batch.quantity_received
        row.cost_price = batch.cost_price
        await self._session.flush()

    async def get(self, batch_id: UUID) -> ProductBatch | None:
        stmt = select(ProductBatchORM).where(
            ProductBatchORM.id == batch_id,
            ProductBatchORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _batch_to_domain(row) if row is not None else None

    async def find_by_lot(self, drug_id: UUID, branch_id: UUID, lot_no: str) -> ProductBatch | None:
        stmt = select(ProductBatchORM).where(
            ProductBatchORM.drug_id == drug_id,
            ProductBatchORM.branch_id == branch_id,
            ProductBatchORM.lot_no == lot_no,
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

    async def stock_report(
        self,
        tenant_id: UUID,
        *,
        branch_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[BatchStockRow]:
        """Batches with on-hand > 0, tenant-wide by default — a deliberate widening
        from the branch-only scope of :meth:`near_expiry`/:meth:`on_hand`: this is a
        chain-level report surface (PROJECT_STATE §7an), not an operational,
        single-branch read. ``batch_id`` breaks ties so paging stays stable when two
        batches share an ``expiry_date``."""
        stmt = (
            select(
                ProductBatchORM.id,
                ProductBatchORM.drug_id,
                ProductBatchORM.branch_id,
                ProductBatchORM.lot_no,
                ProductBatchORM.expiry_date,
                StockBalanceORM.quantity,
            )
            .join(StockBalanceORM, StockBalanceORM.batch_id == ProductBatchORM.id)
            .where(
                ProductBatchORM.tenant_id == tenant_id,
                StockBalanceORM.quantity > 0,
            )
        )
        if branch_id is not None:
            stmt = stmt.where(ProductBatchORM.branch_id == branch_id)
        stmt = (
            stmt.order_by(ProductBatchORM.expiry_date, ProductBatchORM.id)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            BatchStockRow(
                batch_id=r[0],
                drug_id=r[1],
                branch_id=r[2],
                lot_no=r[3],
                expiry_date=r[4],
                quantity=r[5],
            )
            for r in rows
        ]


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

    async def exists_for_ref(self, ref_type: str, ref_id: UUID) -> bool:
        stmt = select(StockMovementORM.id).where(
            StockMovementORM.ref_type == ref_type,
            StockMovementORM.ref_id == ref_id,
            StockMovementORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).first()
        return row is not None


class SqlAlchemyBalanceRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def adjust(
        self, drug_id: UUID, batch_id: UUID, branch_id: UUID, tenant_id: UUID, delta: Decimal
    ) -> Decimal:
        """One statement does the whole job: read, guard and write, atomically.

        The previous shape — ``SELECT`` the row, add *delta* in Python, write it
        back — is the textbook lost update (audit B-01), and no amount of care in
        the calling code can fix it: between the read and the write another
        transaction commits, and its subtraction disappears without a trace. Two
        counters each selling 10 out of 100 left **90** on the books.

        Here the arithmetic happens **inside** the ``UPDATE``, so Postgres takes
        the row lock for the duration and the second writer re-reads the value the
        first one committed: 100 − 10 − 10 is 80. The ``quantity + delta >= 0``
        predicate rides along in the same statement and is what stops an oversell
        (audit B-04) — a check placed before the write would be another
        check-then-act, i.e. the same bug in a new place.

        Zero rows updated therefore means one of exactly two things, and they need
        telling apart: the row is not there yet (first movement of a batch — insert
        it), or it is there and the guard refused (raise, carrying what *was*
        available).
        """
        where = (
            StockBalanceORM.drug_id == drug_id,
            StockBalanceORM.batch_id == batch_id,
            StockBalanceORM.branch_id == branch_id,
            StockBalanceORM.tenant_id == tenant_id,
        )
        bumped = (
            await self._session.execute(
                update(StockBalanceORM)
                .where(*where, StockBalanceORM.quantity + delta >= 0)
                .values(quantity=StockBalanceORM.quantity + delta)
                .returning(StockBalanceORM.quantity)
                .execution_options(synchronize_session=False)
            )
        ).scalar_one_or_none()
        if bumped is not None:
            return Decimal(bumped)

        current = (
            await self._session.execute(select(StockBalanceORM.quantity).where(*where))
        ).scalar_one_or_none()
        if current is not None or delta < 0:
            raise InsufficientStockError(
                requested=-delta, available=Decimal(current if current is not None else 0)
            )

        # First movement of this batch. A concurrent insert of the same balance row
        # loses to ``uq_balance_batch`` and aborts its own transaction — correct, and
        # in practice unreachable: the batch row itself is created in the same
        # transaction and ``uq_batch_lot`` settles that race first.
        row = StockBalanceORM(
            tenant_id=tenant_id,
            branch_id=branch_id,
            drug_id=drug_id,
            batch_id=batch_id,
            quantity=delta,
        )
        self._session.add(row)
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

    async def on_hand_by_drug(self, branch_id: UUID) -> list[DrugOnHandRow]:
        stmt = (
            select(
                StockBalanceORM.drug_id,
                func.sum(StockBalanceORM.quantity).label("on_hand"),
            )
            .where(
                StockBalanceORM.branch_id == branch_id,
                StockBalanceORM.tenant_id == self._ctx.tenant_id,
            )
            .group_by(StockBalanceORM.drug_id)
            .having(func.sum(StockBalanceORM.quantity) > 0)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            DrugOnHandRow(drug_id=r.drug_id, branch_id=branch_id, on_hand=r.on_hand) for r in rows
        ]


class SqlAlchemyStockReconciliationRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, record: StockReconciliationNeeded) -> None:
        self._session.add(
            StockReconciliationNeededORM(
                id=record.id,
                tenant_id=record.tenant_id,
                branch_id=record.branch_id,
                grn_id=record.grn_id,
                po_item_id=record.po_item_id,
                reason=record.reason,
                occurred_at=record.occurred_at,
                resolved=record.resolved,
            )
        )
        await self._session.flush()

    async def get(self, record_id: UUID, tenant_id: UUID) -> StockReconciliationNeeded | None:
        stmt = select(StockReconciliationNeededORM).where(
            StockReconciliationNeededORM.id == record_id,
            StockReconciliationNeededORM.tenant_id == tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _reconciliation_to_domain(row) if row is not None else None

    async def update(self, record: StockReconciliationNeeded) -> None:
        stmt = select(StockReconciliationNeededORM).where(
            StockReconciliationNeededORM.id == record.id,
            StockReconciliationNeededORM.tenant_id == record.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.resolved = record.resolved
        await self._session.flush()

    async def list(
        self,
        tenant_id: UUID,
        branch_id: UUID,
        *,
        resolved: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StockReconciliationNeeded]:
        stmt = select(StockReconciliationNeededORM).where(
            StockReconciliationNeededORM.tenant_id == tenant_id,
            StockReconciliationNeededORM.branch_id == branch_id,
        )
        if resolved is not None:
            stmt = stmt.where(StockReconciliationNeededORM.resolved == resolved)
        stmt = (
            stmt.order_by(StockReconciliationNeededORM.occurred_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_reconciliation_to_domain(r) for r in rows]


def _reconciliation_to_domain(row: StockReconciliationNeededORM) -> StockReconciliationNeeded:
    return StockReconciliationNeeded(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        grn_id=row.grn_id,
        po_item_id=row.po_item_id,
        reason=row.reason,
        resolved=row.resolved,
        occurred_at=row.occurred_at,
    )


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
