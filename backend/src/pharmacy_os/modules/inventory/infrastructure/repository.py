"""SQLAlchemy inventory repositories, tenant/branch-scoped."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.inventory.domain.counting import CountLine, CountStatus, StockCount
from pharmacy_os.modules.inventory.domain.entities import (
    ProductBatch,
    StockMovement,
    StockReconciliationNeeded,
)
from pharmacy_os.modules.inventory.domain.exceptions import (
    DuplicateMovementError,
    InsufficientStockError,
)
from pharmacy_os.modules.inventory.domain.fefo import BatchAvailability
from pharmacy_os.modules.inventory.domain.ports import (
    BatchStockRow,
    DrugOnHandRow,
    LocationStockRow,
    TomTatO,
)
from pharmacy_os.modules.inventory.infrastructure.models import (
    ProductBatchORM,
    StockAtLocationORM,
    StockBalanceORM,
    StockCountLineORM,
    StockCountORM,
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


_DUPLICATE_REF_MARKERS = ("uq_movement_ref_batch", "ref_id")
"""How the two dialects spell the same violation — measured, not assumed.

Postgres quotes the index: ``duplicate key value violates unique constraint
"uq_movement_ref_batch"``. SQLite, where the test suite runs, names the columns
instead and never the index: ``UNIQUE constraint failed: stock_movements.tenant_id,
stock_movements.ref_type, stock_movements.ref_id, stock_movements.batch_id``
(checked on sqlite 3.45.1). A primary-key collision or a NOT NULL violation
mentions neither marker and so keeps travelling as itself — turning *those* into
"already done" would bury a real bug under an idempotency skip.
"""


def _is_duplicate_ref(exc: IntegrityError) -> bool:
    """True when ``uq_movement_ref_batch`` is what fired, not some other constraint."""
    message = str(exc.orig)
    return any(marker in message for marker in _DUPLICATE_REF_MARKERS)


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
                from_location_id=movement.from_location_id,
                to_location_id=movement.to_location_id,
            )
        )
        try:
            await self._session.flush()
        except IntegrityError as exc:
            if movement.ref_id is None or not _is_duplicate_ref(exc):
                raise
            raise DuplicateMovementError(movement.ref_type or "", movement.ref_id) from exc

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

    async def for_batch(self, batch_id: UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(StockBalanceORM.quantity), 0)).where(
            StockBalanceORM.tenant_id == self._ctx.tenant_id,
            StockBalanceORM.branch_id == self._ctx.branch_id,
            StockBalanceORM.batch_id == batch_id,
        )
        return Decimal(str((await self._session.execute(stmt)).scalar_one()))

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


class SqlAlchemyStockAtLocationRepository:
    """Sổ **nằm ở đâu**. Luôn ≤ ``stock_balances`` — bất biến kiểm ở tầng ứng dụng."""

    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def put_away(
        self, *, drug_id: UUID, batch_id: UUID, location_id: UUID, delta: Decimal
    ) -> None:
        """Cộng dồn *delta* vào một (lô, ô), tạo dòng nếu chưa có.

        🔴 Số học nằm **trong** câu ``UPDATE``, không phải đọc-rồi-ghi ở Python — cùng lý do
        đã ghi ở :meth:`SqlAlchemyBalanceRepository.adjust`: đọc rồi ghi là lost update kinh
        điển, và hai người cất hàng cùng lúc sẽ nuốt mất một lượt mà không để lại dấu.
        """
        stmt = (
            update(StockAtLocationORM)
            .where(
                StockAtLocationORM.tenant_id == self._ctx.tenant_id,
                StockAtLocationORM.branch_id == self._ctx.branch_id,
                StockAtLocationORM.batch_id == batch_id,
                StockAtLocationORM.location_id == location_id,
            )
            .values(quantity=StockAtLocationORM.quantity + delta)
        )
        kq = await self._session.execute(stmt)
        # `CursorResult` mới có `rowcount`; `Result` chung thì không, nên mypy --strict
        # từ chối. Ép kiểu ở đây thay vì bỏ qua bằng `type: ignore`: một câu UPDATE luôn
        # trả về CursorResult, và nói ra điều đó rõ hơn là im lặng tắt phép kiểm.
        if cast("CursorResult[Any]", kq).rowcount == 0:
            self._session.add(
                StockAtLocationORM(
                    tenant_id=self._ctx.tenant_id,
                    branch_id=self._ctx.branch_id,
                    drug_id=drug_id,
                    batch_id=batch_id,
                    location_id=location_id,
                    quantity=delta,
                )
            )
        await self._session.flush()

    async def total_for_batch(self, batch_id: UUID) -> Decimal:
        stmt = select(func.coalesce(func.sum(StockAtLocationORM.quantity), 0)).where(
            StockAtLocationORM.tenant_id == self._ctx.tenant_id,
            StockAtLocationORM.branch_id == self._ctx.branch_id,
            StockAtLocationORM.batch_id == batch_id,
        )
        return Decimal(str((await self._session.execute(stmt)).scalar_one()))

    async def _rows(self, *conds: object) -> list[LocationStockRow]:
        """Ghép sẵn lô + hạn dùng ngay trong truy vấn.

        Nối bảng ở đây thay vì tra lần hai ở tầng ứng dụng: người đứng quầy cần **ô, lô,
        HSD, số lượng** cùng một lúc, và trả về một nửa rồi bắt bên gọi đi tìm nốt là cách
        đẻ ra N+1 lượt gọi cho một màn hình đang có người đứng chờ.
        """
        stmt = (
            select(
                StockAtLocationORM.drug_id,
                StockAtLocationORM.batch_id,
                StockAtLocationORM.location_id,
                ProductBatchORM.lot_no,
                ProductBatchORM.expiry_date,
                StockAtLocationORM.quantity,
            )
            .join(ProductBatchORM, ProductBatchORM.id == StockAtLocationORM.batch_id)
            .where(
                StockAtLocationORM.tenant_id == self._ctx.tenant_id,
                StockAtLocationORM.branch_id == self._ctx.branch_id,
                StockAtLocationORM.quantity > 0,
                *conds,  # type: ignore[arg-type]
            )
            .order_by(ProductBatchORM.expiry_date, ProductBatchORM.lot_no)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            LocationStockRow(
                drug_id=r[0],
                batch_id=r[1],
                location_id=r[2],
                lot_no=r[3],
                expiry_date=r[4],
                quantity=r[5],
            )
            for r in rows
        ]

    async def rows_for_drug(self, drug_id: UUID) -> Sequence[LocationStockRow]:
        return await self._rows(StockAtLocationORM.drug_id == drug_id)

    async def rows_at_location(self, location_id: UUID) -> Sequence[LocationStockRow]:
        return await self._rows(StockAtLocationORM.location_id == location_id)

    async def tom_tat_moi_o(self) -> Sequence[TomTatO]:
        """Gộp ở tầng CSDL — xem `StockAtLocationRepository.tom_tat_moi_o`."""
        stmt = (
            select(
                StockAtLocationORM.location_id,
                func.count(StockAtLocationORM.batch_id),
                func.sum(StockAtLocationORM.quantity),
                func.min(ProductBatchORM.expiry_date),
            )
            .join(ProductBatchORM, ProductBatchORM.id == StockAtLocationORM.batch_id)
            .where(
                StockAtLocationORM.tenant_id == self._ctx.tenant_id,
                StockAtLocationORM.branch_id == self._ctx.branch_id,
                StockAtLocationORM.quantity > 0,
            )
            .group_by(StockAtLocationORM.location_id)
        )
        return [
            TomTatO(location_id=r[0], so_lo=r[1], tong_so_luong=r[2], hsd_gan_nhat=r[3])
            for r in (await self._session.execute(stmt)).all()
        ]


class SqlAlchemyStockCountRepository:
    """Phiên kiểm kê + dòng của nó, lưu như **một cụm**.

    Không có repo riêng cho dòng: một dòng kiểm kê ngoài phiên của nó là vô nghĩa, và mở
    một cửa để sửa dòng lẻ là mở một đường đi vòng qua các quy tắc trạng thái trong
    :class:`StockCount`.
    """

    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, count: StockCount) -> None:
        self._session.add(
            StockCountORM(
                id=count.id,
                tenant_id=count.tenant_id,
                branch_id=count.branch_id,
                location_id=count.location_id,
                status=str(count.status),
                counted_by=count.counted_by,
                decided_by=count.decided_by,
                submitted_at=count.submitted_at,
                decided_at=count.decided_at,
            )
        )
        for dong in count.lines:
            self._session.add(self._dong_orm(count, dong))
        await self._session.flush()

    def _dong_orm(self, count: StockCount, dong: CountLine) -> StockCountLineORM:
        return StockCountLineORM(
            id=dong.id,
            tenant_id=count.tenant_id,
            branch_id=count.branch_id,
            count_id=count.id,
            batch_id=dong.batch_id,
            counted_qty=dong.counted_qty,
            system_qty=dong.system_qty,
        )

    async def get(self, count_id: UUID) -> StockCount | None:
        row = (
            await self._session.execute(
                select(StockCountORM).where(
                    StockCountORM.id == count_id,
                    StockCountORM.tenant_id == self._ctx.tenant_id,
                    StockCountORM.branch_id == self._ctx.branch_id,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return await self._voi_dong([row])

    async def _voi_dong(self, rows: list[StockCountORM]) -> StockCount:
        cum = await self._nap_dong(rows)
        return cum[0]

    async def _nap_dong(self, rows: Sequence[StockCountORM]) -> list[StockCount]:
        """Nạp dòng cho NHIỀU phiên trong MỘT lượt truy vấn.

        Một vòng lặp gọi `get` cho từng phiên là bài toán N+1 kinh điển; màn danh sách hiện
        50 phiên sẽ thành 51 lượt đi-về.
        """
        if not rows:
            return []
        dong_rows = (
            (
                await self._session.execute(
                    select(StockCountLineORM)
                    .where(StockCountLineORM.count_id.in_([r.id for r in rows]))
                    .order_by(StockCountLineORM.id)
                )
            )
            .scalars()
            .all()
        )
        theo_phien: dict[UUID, list[CountLine]] = {}
        for d in dong_rows:
            theo_phien.setdefault(d.count_id, []).append(
                CountLine(
                    id=d.id,
                    batch_id=d.batch_id,
                    counted_qty=d.counted_qty,
                    system_qty=d.system_qty,
                )
            )
        return [
            StockCount(
                id=r.id,
                tenant_id=r.tenant_id,
                branch_id=r.branch_id,
                location_id=r.location_id,
                counted_by=r.counted_by,
                status=CountStatus(r.status),
                lines=theo_phien.get(r.id, []),
                decided_by=r.decided_by,
                created_at=r.created_at,
                submitted_at=r.submitted_at,
                decided_at=r.decided_at,
            )
            for r in rows
        ]

    async def update(self, count: StockCount) -> None:
        await self._session.execute(
            update(StockCountORM)
            .where(
                StockCountORM.id == count.id,
                StockCountORM.tenant_id == self._ctx.tenant_id,
            )
            .values(
                status=str(count.status),
                decided_by=count.decided_by,
                submitted_at=count.submitted_at,
                decided_at=count.decided_at,
            )
        )
        # Dòng: xoá rồi ghi lại. Cụm này nhỏ (một ô, vài chục lô) và luôn được ghi trọn vẹn
        # trong một giao dịch — so từng dòng để ra UPDATE/INSERT/DELETE riêng là thêm ba
        # nhánh có thể sai để đổi lấy một khoản tiết kiệm không đo được.
        await self._session.execute(
            delete(StockCountLineORM).where(StockCountLineORM.count_id == count.id)
        )
        for dong in count.lines:
            self._session.add(self._dong_orm(count, dong))
        await self._session.flush()

    async def list(self, *, status: str | None, limit: int, offset: int) -> Sequence[StockCount]:
        stmt = select(StockCountORM).where(
            StockCountORM.tenant_id == self._ctx.tenant_id,
            StockCountORM.branch_id == self._ctx.branch_id,
        )
        if status is not None:
            stmt = stmt.where(StockCountORM.status == status)
        rows = (
            (
                await self._session.execute(
                    stmt.order_by(StockCountORM.created_at.desc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return await self._nap_dong(list(rows))
