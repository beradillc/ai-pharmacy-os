"""SQLAlchemy implementations of the procurement repository ports, tenant-scoped."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.procurement.domain import (
    GoodsReceiptNote,
    PurchaseOrder,
    PurchaseOrderStatus,
    Supplier,
)
from pharmacy_os.modules.procurement.infrastructure.mappers import (
    goods_receipt_to_domain,
    goods_receipt_to_orm,
    purchase_order_to_domain,
    purchase_order_to_orm,
    supplier_to_domain,
    supplier_to_orm,
)
from pharmacy_os.modules.procurement.infrastructure.models import (
    GoodsReceiptItemORM,
    GoodsReceiptORM,
    PurchaseOrderCounterORM,
    PurchaseOrderItemORM,
    PurchaseOrderORM,
    SupplierORM,
)


class SqlAlchemySupplierRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, supplier: Supplier) -> None:
        self._session.add(supplier_to_orm(supplier))
        await self._session.flush()

    async def update(self, supplier: Supplier) -> None:
        stmt = select(SupplierORM).where(
            SupplierORM.id == supplier.id, SupplierORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.name = supplier.name
        row.tax_code = supplier.tax_code
        row.contact_name = supplier.contact_name
        row.phone = supplier.phone
        row.email = supplier.email
        row.address = supplier.address
        row.is_active = supplier.is_active
        await self._session.flush()

    async def get(self, supplier_id: UUID) -> Supplier | None:
        stmt = select(SupplierORM).where(
            SupplierORM.id == supplier_id, SupplierORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return supplier_to_domain(row) if row is not None else None

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[Supplier]:
        stmt = (
            select(SupplierORM)
            .where(SupplierORM.tenant_id == self._ctx.tenant_id)
            .order_by(SupplierORM.name)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [supplier_to_domain(r) for r in rows]

    async def names_by_ids(self, supplier_ids: Sequence[UUID]) -> dict[UUID, str]:
        if not supplier_ids:
            return {}
        stmt = select(SupplierORM.id, SupplierORM.name).where(
            SupplierORM.id.in_(supplier_ids), SupplierORM.tenant_id == self._ctx.tenant_id
        )
        rows = (await self._session.execute(stmt)).all()
        return {row.id: row.name for row in rows}


#: Width of the numeric part of a PO code. Four digits reads well on a screen and over
#: the phone; the format widens rather than wraps past PO-9999 (``PO-10000``), so the
#: number stays unique — never reused — which is the only property that matters.
_PO_CODE_DIGITS = 4


class SqlAlchemyPurchaseOrderRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def next_code(self) -> str:
        """Allocate this tenant's next PO number.

        The arithmetic lives **inside** the ``UPDATE`` (``last_value = last_value + 1``),
        so the row lock that makes it safe is held by the statement itself — no
        read-then-write gap for a second transaction to slip into. This is the same
        shape as the stock fix in F-5 (audit B-01), and it is chosen for the same
        reason: a SELECT-then-UPDATE here would hand two pharmacists the same order
        number under exactly the load where it matters.

        The first PO of a tenant has no counter row yet. That insert races too, so a
        loser sees the unique violation on ``tenant_id`` and simply retries the UPDATE,
        which by then finds the row the winner created.
        """
        for _ in range(2):
            stmt = (
                update(PurchaseOrderCounterORM)
                .where(PurchaseOrderCounterORM.tenant_id == self._ctx.tenant_id)
                .values(last_value=PurchaseOrderCounterORM.last_value + 1)
                .returning(PurchaseOrderCounterORM.last_value)
            )
            value = (await self._session.execute(stmt)).scalar_one_or_none()
            if value is not None:
                return f"PO-{value:0{_PO_CODE_DIGITS}d}"

            savepoint = await self._session.begin_nested()
            try:
                self._session.add(
                    PurchaseOrderCounterORM(tenant_id=self._ctx.tenant_id, last_value=1)
                )
                await self._session.flush()
            except IntegrityError:
                # Another transaction created the counter first — roll back only this
                # insert (not the caller's work) and go round to the UPDATE branch.
                await savepoint.rollback()
                continue
            else:
                await savepoint.commit()
                return f"PO-{1:0{_PO_CODE_DIGITS}d}"

        raise RuntimeError("Không cấp phát được mã đơn mua sau 2 lần thử")

    async def add(self, purchase_order: PurchaseOrder) -> None:
        self._session.add(purchase_order_to_orm(purchase_order))
        await self._session.flush()

    async def update(self, purchase_order: PurchaseOrder) -> None:
        """Persist status + each existing line's ``quantity_received``.

        Items are added only while ``DRAFT`` (mirrors ``add_po_item``, which also
        goes through this method) or accumulate via :meth:`PurchaseOrder.apply_receipt`
        — never removed — so a straight id-keyed sync (no diff/dedup) is sufficient.
        """
        stmt = select(PurchaseOrderORM).where(
            PurchaseOrderORM.id == purchase_order.id,
            PurchaseOrderORM.tenant_id == self._ctx.tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.status = purchase_order.status.value
        row.ordered_at = purchase_order.ordered_at

        existing_by_id = {it.id: it for it in row.items}
        for item in purchase_order.items:
            existing = existing_by_id.get(item.id)
            if existing is None:
                row.items.append(
                    PurchaseOrderItemORM(
                        id=item.id,
                        purchase_order_id=purchase_order.id,
                        drug_id=item.drug_id,
                        quantity_ordered=item.quantity_ordered,
                        unit_price=item.unit_price,
                        quantity_received=item.quantity_received,
                    )
                )
            else:
                existing.quantity_received = item.quantity_received
        await self._session.flush()

    async def get(self, po_id: UUID) -> PurchaseOrder | None:
        stmt = select(PurchaseOrderORM).where(
            PurchaseOrderORM.id == po_id, PurchaseOrderORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return purchase_order_to_domain(row) if row is not None else None

    async def count_by_status(self, status: PurchaseOrderStatus, branch_id: UUID) -> int:
        stmt = select(func.count(PurchaseOrderORM.id)).where(
            PurchaseOrderORM.tenant_id == self._ctx.tenant_id,
            PurchaseOrderORM.branch_id == branch_id,
            PurchaseOrderORM.status == status.value,
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def last_supplier_for_drug(self, drug_id: UUID) -> UUID | None:
        # "Placed" = past DRAFT: a still-draft PO isn't a real supplier relationship.
        # Most recent by created_at; tenant-wide (a supplier serves the whole chain).
        stmt = (
            select(PurchaseOrderORM.supplier_id)
            .join(
                PurchaseOrderItemORM,
                PurchaseOrderItemORM.purchase_order_id == PurchaseOrderORM.id,
            )
            .where(
                PurchaseOrderORM.tenant_id == self._ctx.tenant_id,
                PurchaseOrderORM.status != PurchaseOrderStatus.DRAFT.value,
                PurchaseOrderItemORM.drug_id == drug_id,
            )
            .order_by(PurchaseOrderORM.created_at.desc())
            .limit(1)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()


class SqlAlchemyGoodsReceiptRepository:
    def __init__(self, session: AsyncSession, ctx: RequestContext) -> None:
        self._session = session
        self._ctx = ctx

    async def add(self, receipt: GoodsReceiptNote) -> None:
        self._session.add(goods_receipt_to_orm(receipt))
        await self._session.flush()

    async def update(self, receipt: GoodsReceiptNote) -> None:
        """Persist status + append any newly added lines (insert-only while ``DRAFT``)."""
        stmt = select(GoodsReceiptORM).where(
            GoodsReceiptORM.id == receipt.id, GoodsReceiptORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one()
        row.status = receipt.status.value

        existing_ids = {it.id for it in row.items}
        for item in receipt.items:
            if item.id not in existing_ids:
                row.items.append(
                    GoodsReceiptItemORM(
                        id=item.id,
                        goods_receipt_id=receipt.id,
                        po_item_id=item.po_item_id,
                        drug_id=item.drug_id,
                        quantity_received=item.quantity_received,
                        lot_no=item.lot_no,
                        expiry_date=item.expiry_date,
                        unit_cost=item.unit_cost,
                        mfg_date=item.mfg_date,
                    )
                )
        await self._session.flush()

    async def get(self, grn_id: UUID) -> GoodsReceiptNote | None:
        stmt = select(GoodsReceiptORM).where(
            GoodsReceiptORM.id == grn_id, GoodsReceiptORM.tenant_id == self._ctx.tenant_id
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return goods_receipt_to_domain(row) if row is not None else None
