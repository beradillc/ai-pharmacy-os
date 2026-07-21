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

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.inventory.application.dto import (
    AllocationOutput,
    DispenseInput,
    DispenseOutput,
    NearExpiryItem,
    ReceiptOutput,
    ReceiveStockInput,
)
from pharmacy_os.modules.inventory.domain import (
    InsufficientStockError,
    LowStockDetected,
    MovementType,
    ProductBatch,
    StockMovedIn,
    StockMovedOut,
    StockMovement,
    allocate_fefo,
)
from pharmacy_os.modules.inventory.domain.ports import (
    BalanceRepository,
    BatchRepository,
    MovementRepository,
)

UowFactory = Callable[[], UnitOfWork]
BatchRepoFactory = Callable[[UnitOfWork, RequestContext], BatchRepository]
MovementRepoFactory = Callable[[UnitOfWork, RequestContext], MovementRepository]
BalanceRepoFactory = Callable[[UnitOfWork, RequestContext], BalanceRepository]


class InventoryService:
    def __init__(
        self,
        uow_factory: UowFactory,
        batch_repo_factory: BatchRepoFactory,
        movement_repo_factory: MovementRepoFactory,
        balance_repo_factory: BalanceRepoFactory,
        *,
        reorder_point: Decimal = Decimal("0"),
    ) -> None:
        self._uow_factory = uow_factory
        self._batches = batch_repo_factory
        self._movements = movement_repo_factory
        self._balances = balance_repo_factory
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
