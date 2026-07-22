"""Inventory use-cases: receiving stock and FEFO dispensing.

Stock levels are event-sourced: every change appends a :class:`StockMovement`
and projects onto the balance. Domain events are collected on the unit of work
and published only after a successful commit.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import structlog

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.inventory.application.dto import (
    AllocationOutput,
    DispenseInput,
    DispenseOutput,
    GoodsReceiptLine,
    NearExpiryItem,
    ReceiptOutput,
    ReceiveStockInput,
    SaleDispenseItem,
)
from pharmacy_os.modules.inventory.domain import (
    InsufficientStockError,
    LowStockDetected,
    MovementType,
    ProductBatch,
    StockMovedIn,
    StockMovedOut,
    StockMovement,
    StockReconciliationNeeded,
    StockShortfallDetected,
    allocate_fefo,
)
from pharmacy_os.modules.inventory.domain.ports import (
    BalanceRepository,
    BatchRepository,
    MovementRepository,
    StockReconciliationRepository,
)

_log = structlog.get_logger("inventory.goods_receipt")

UowFactory = Callable[[], UnitOfWork]
BatchRepoFactory = Callable[[UnitOfWork, RequestContext], BatchRepository]
MovementRepoFactory = Callable[[UnitOfWork, RequestContext], MovementRepository]
BalanceRepoFactory = Callable[[UnitOfWork, RequestContext], BalanceRepository]
ReconciliationRepoFactory = Callable[[UnitOfWork, RequestContext], StockReconciliationRepository]


class InventoryService:
    def __init__(
        self,
        uow_factory: UowFactory,
        batch_repo_factory: BatchRepoFactory,
        movement_repo_factory: MovementRepoFactory,
        balance_repo_factory: BalanceRepoFactory,
        reconciliation_repo_factory: ReconciliationRepoFactory,
        *,
        reorder_point: Decimal = Decimal("0"),
    ) -> None:
        self._uow_factory = uow_factory
        self._batches = batch_repo_factory
        self._movements = movement_repo_factory
        self._balances = balance_repo_factory
        self._reconciliations = reconciliation_repo_factory
        self._reorder_point = reorder_point

    async def receive_stock(self, data: ReceiveStockInput, ctx: RequestContext) -> ReceiptOutput:
        """Receive a batch: create it, append an IN movement, project the balance.

        Emits :class:`StockMovedIn` after commit. Raises :class:`ValidationError`
        if the received quantity is not strictly positive.
        """
        require_permission(ctx, "inventory.receive")
        if data.quantity <= 0:
            raise ValidationError("Số lượng nhập phải > 0")

        batch = ProductBatch(
            drug_id=data.drug_id,
            branch_id=ctx.branch_id,
            tenant_id=ctx.tenant_id,
            lot_no=data.lot_no,
            expiry_date=data.expiry_date,
            mfg_date=data.mfg_date,
            cost_price=data.cost_price,
            quantity_received=data.quantity,
        )
        async with self._uow_factory() as uow:
            batches = self._batches(uow, ctx)
            movements = self._movements(uow, ctx)
            balances = self._balances(uow, ctx)

            await batches.add(batch)
            await movements.add(
                StockMovement(
                    drug_id=batch.drug_id,
                    batch_id=batch.id,
                    branch_id=ctx.branch_id,
                    tenant_id=ctx.tenant_id,
                    type=MovementType.IN,
                    quantity=data.quantity,
                    ref_type="GRN",
                )
            )
            await balances.adjust(
                batch.drug_id, batch.id, ctx.branch_id, ctx.tenant_id, data.quantity
            )
            on_hand = await balances.on_hand(batch.drug_id, ctx.branch_id)
            uow.collect(
                StockMovedIn(
                    tenant_id=ctx.tenant_id,
                    drug_id=batch.drug_id,
                    batch_id=batch.id,
                    branch_id=ctx.branch_id,
                    quantity=data.quantity,
                )
            )
            await uow.commit()

        return ReceiptOutput(
            batch_id=batch.id,
            drug_id=batch.drug_id,
            quantity_received=data.quantity,
            on_hand=on_hand,
        )

    async def dispense_stock(self, data: DispenseInput, ctx: RequestContext) -> DispenseOutput:
        """Dispense a quantity using FEFO across the drug's non-expired batches.

        Appends one OUT movement per allocated batch and projects the balances.
        Emits :class:`StockMovedOut` (and :class:`LowStockDetected` when the new
        on-hand falls to/below the reorder point) after commit. Raises
        :class:`ValidationError` for a non-positive quantity and
        :class:`ConflictError` when available stock is insufficient — in which
        case the whole transaction rolls back untouched.
        """
        require_permission(ctx, "inventory.dispense")
        if data.quantity <= 0:
            raise ValidationError("Số lượng xuất phải > 0")

        async with self._uow_factory() as uow:
            batches = self._batches(uow, ctx)
            movements = self._movements(uow, ctx)
            balances = self._balances(uow, ctx)

            avail = await batches.availabilities(
                data.drug_id, ctx.branch_id, not_expired_on=date.today()
            )
            try:
                allocations = allocate_fefo(avail, data.quantity)
            except InsufficientStockError as exc:
                raise ConflictError(str(exc)) from exc

            for alloc in allocations:
                await movements.add(
                    StockMovement(
                        drug_id=data.drug_id,
                        batch_id=alloc.batch_id,
                        branch_id=ctx.branch_id,
                        tenant_id=ctx.tenant_id,
                        type=MovementType.OUT,
                        quantity=alloc.quantity,
                        ref_type=data.ref_type,
                        ref_id=data.ref_id,
                    )
                )
                await balances.adjust(
                    data.drug_id, alloc.batch_id, ctx.branch_id, ctx.tenant_id, -alloc.quantity
                )

            on_hand = await balances.on_hand(data.drug_id, ctx.branch_id)
            uow.collect(
                StockMovedOut(
                    tenant_id=ctx.tenant_id,
                    drug_id=data.drug_id,
                    branch_id=ctx.branch_id,
                    quantity=data.quantity,
                )
            )
            if on_hand <= self._reorder_point:
                uow.collect(
                    LowStockDetected(
                        tenant_id=ctx.tenant_id,
                        drug_id=data.drug_id,
                        branch_id=ctx.branch_id,
                        on_hand=on_hand,
                        reorder_point=self._reorder_point,
                    )
                )
            await uow.commit()

        return DispenseOutput(
            drug_id=data.drug_id,
            dispensed=data.quantity,
            on_hand=on_hand,
            allocations=[
                AllocationOutput(batch_id=a.batch_id, quantity=a.quantity) for a in allocations
            ],
        )

    async def dispense_for_sale(
        self, items: list[SaleDispenseItem], order_id: UUID, ctx: RequestContext
    ) -> None:
        """React to a completed sale: dispense each line by FEFO, idempotently.

        Idempotent on ``order_id`` (skips if already dispensed for this sale). A
        line exceeding available stock is dispensed as far as possible and a
        :class:`StockShortfallDetected` event flags the remainder — the sale is
        never blocked (it is already committed) and stock never goes negative.
        """
        require_permission(ctx, "inventory.dispense")
        async with self._uow_factory() as uow:
            batches = self._batches(uow, ctx)
            movements = self._movements(uow, ctx)
            balances = self._balances(uow, ctx)

            if await movements.exists_for_ref("sale", order_id):
                return  # this sale was already dispensed

            for item in items:
                if item.quantity <= 0:
                    continue
                avail = await batches.availabilities(
                    item.drug_id, ctx.branch_id, not_expired_on=date.today()
                )
                total = sum((a.available for a in avail), Decimal("0"))
                take = min(item.quantity, total)
                if take > 0:
                    for alloc in allocate_fefo(avail, take):
                        await movements.add(
                            StockMovement(
                                drug_id=item.drug_id,
                                batch_id=alloc.batch_id,
                                branch_id=ctx.branch_id,
                                tenant_id=ctx.tenant_id,
                                type=MovementType.OUT,
                                quantity=alloc.quantity,
                                ref_type="sale",
                                ref_id=order_id,
                            )
                        )
                        await balances.adjust(
                            item.drug_id,
                            alloc.batch_id,
                            ctx.branch_id,
                            ctx.tenant_id,
                            -alloc.quantity,
                        )
                    uow.collect(
                        StockMovedOut(
                            tenant_id=ctx.tenant_id,
                            drug_id=item.drug_id,
                            branch_id=ctx.branch_id,
                            quantity=take,
                        )
                    )
                if item.quantity > total:
                    uow.collect(
                        StockShortfallDetected(
                            tenant_id=ctx.tenant_id,
                            drug_id=item.drug_id,
                            branch_id=ctx.branch_id,
                            requested=item.quantity,
                            available=total,
                            ref_type="sale",
                            ref_id=order_id,
                        )
                    )
            await uow.commit()

    async def receive_from_goods_receipt(
        self, lines: list[GoodsReceiptLine], grn_id: UUID, ctx: RequestContext
    ) -> None:
        """React to a confirmed goods-receipt note: create one batch per line.

        Idempotent on ``grn_id`` (skips entirely if this GRN's stock-in already
        ran — every IN movement it writes carries ``ref_type="grn"``,
        ``ref_id=grn_id``). A line whose ``(drug_id, branch_id, lot_no)`` already
        exists is **skipped, not merged** (consistent with the ``uq_batch_lot``
        constraint the manual receive relies on) and flagged in
        ``stock_reconciliation_needed``. Any unexpected failure aborts the whole
        transaction and is likewise flagged best-effort in a fresh transaction —
        the GRN is already confirmed, so a silent stock gap is never left behind.
        """
        require_permission(ctx, "inventory.receive")
        try:
            async with self._uow_factory() as uow:
                batches = self._batches(uow, ctx)
                movements = self._movements(uow, ctx)
                balances = self._balances(uow, ctx)
                reconciliations = self._reconciliations(uow, ctx)

                if await movements.exists_for_ref("grn", grn_id):
                    return  # this GRN's stock-in already ran

                for line in lines:
                    if line.quantity <= 0:
                        continue
                    existing = await batches.find_by_lot(line.drug_id, ctx.branch_id, line.lot_no)
                    if existing is not None:
                        await reconciliations.add(
                            StockReconciliationNeeded(
                                tenant_id=ctx.tenant_id,
                                branch_id=ctx.branch_id,
                                grn_id=grn_id,
                                po_item_id=line.po_item_id,
                                reason=(
                                    f"lot_collision: drug={line.drug_id} lot={line.lot_no} "
                                    f"trùng lô đã có (batch {existing.id}); bỏ qua, không gộp"
                                ),
                            )
                        )
                        continue

                    batch = ProductBatch(
                        drug_id=line.drug_id,
                        branch_id=ctx.branch_id,
                        tenant_id=ctx.tenant_id,
                        lot_no=line.lot_no,
                        expiry_date=line.expiry_date,
                        mfg_date=line.mfg_date,
                        cost_price=line.unit_cost,
                        quantity_received=line.quantity,
                    )
                    await batches.add(batch)
                    await movements.add(
                        StockMovement(
                            drug_id=line.drug_id,
                            batch_id=batch.id,
                            branch_id=ctx.branch_id,
                            tenant_id=ctx.tenant_id,
                            type=MovementType.IN,
                            quantity=line.quantity,
                            ref_type="grn",
                            ref_id=grn_id,
                        )
                    )
                    await balances.adjust(
                        line.drug_id, batch.id, ctx.branch_id, ctx.tenant_id, line.quantity
                    )
                    uow.collect(
                        StockMovedIn(
                            tenant_id=ctx.tenant_id,
                            drug_id=line.drug_id,
                            batch_id=batch.id,
                            branch_id=ctx.branch_id,
                            quantity=line.quantity,
                        )
                    )
                await uow.commit()
        except Exception as exc:  # noqa: BLE001 — GRN already confirmed; flag & degrade
            _log.error("grn_stock_in_failed", grn_id=str(grn_id), error=str(exc))
            await self._flag_stock_in_failure(
                grn_id, f"unexpected_error: {type(exc).__name__}: {exc}", ctx
            )

    async def _flag_stock_in_failure(self, grn_id: UUID, reason: str, ctx: RequestContext) -> None:
        """Best-effort: record a whole-GRN stock-in failure in its own transaction.

        Used only when the main receive transaction aborted (its writes rolled
        back). ``po_item_id`` is ``None`` — the failure isn't tied to one line.
        If even this write fails there is nothing left to do but log.
        """
        try:
            async with self._uow_factory() as uow:
                reconciliations = self._reconciliations(uow, ctx)
                await reconciliations.add(
                    StockReconciliationNeeded(
                        tenant_id=ctx.tenant_id,
                        branch_id=ctx.branch_id,
                        grn_id=grn_id,
                        po_item_id=None,
                        reason=reason,
                    )
                )
                await uow.commit()
        except Exception:  # noqa: BLE001 — last resort, nothing else to fall back to
            _log.exception("grn_stock_in_flag_failed", grn_id=str(grn_id))

    async def on_hand(self, drug_id: UUID, ctx: RequestContext) -> Decimal:
        """Total on-hand of a drug at the caller's branch (0 if none exists)."""
        require_permission(ctx, "inventory.read")
        async with self._uow_factory() as uow:
            balances = self._balances(uow, ctx)
            return await balances.on_hand(drug_id, ctx.branch_id)

    async def list_near_expiry(
        self, ctx: RequestContext, *, within_days: int = 90
    ) -> list[NearExpiryItem]:
        """List the branch's batches expiring on/before today + *within_days*."""
        require_permission(ctx, "inventory.read")
        before = date.today() + timedelta(days=within_days)
        async with self._uow_factory() as uow:
            batches = self._batches(uow, ctx)
            found = await batches.near_expiry(ctx.branch_id, before=before)
        return [
            NearExpiryItem(
                batch_id=b.id,
                drug_id=b.drug_id,
                lot_no=b.lot_no,
                expiry_date=b.expiry_date,
                quantity_received=b.quantity_received,
            )
            for b in found
        ]
