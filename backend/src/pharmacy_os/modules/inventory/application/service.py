"""Inventory use-cases: receiving stock and FEFO dispensing.

Stock levels are event-sourced: every change appends a :class:`StockMovement`
and projects onto the balance. Domain events are collected on the unit of work
and published only after a successful commit.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Sequence
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import structlog

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.inventory.application.dto import (
    AllocationOutput,
    DispenseInput,
    DispenseOutput,
    GoodsReceiptLine,
    NearExpiryItem,
    PutAwayOutput,
    ReceiptOutput,
    ReceiveStockInput,
    ReconciliationOutput,
    SaleDispenseItem,
    StockReportItem,
)
from pharmacy_os.modules.inventory.domain import (
    ChangLay,
    DuplicateMovementError,
    InsufficientStockError,
    LocationInfoProvider,
    LocationStockRow,
    LotExpiryMismatchError,
    LowStockDetected,
    MovementType,
    PickCandidate,
    ProductBatch,
    PutAwayError,
    ReconciliationAlreadyResolvedError,
    StockAtLocationRepository,
    StockCountRepository,
    StockMovedIn,
    StockMovedOut,
    StockMovement,
    StockReconciliationNeeded,
    StockShortfallDetected,
    TomTatO,
    allocate_fefo,
    allocate_from_locations,
    chua_xep_o,
    ensure_can_put_away,
    gom_lo_trinh,
    sort_pick_candidates,
)
from pharmacy_os.modules.inventory.domain.counting import (
    CountError,
    CountStatus,
    StockCount,
)
from pharmacy_os.modules.inventory.domain.ports import (
    BalanceRepository,
    BatchRepository,
    DrugOnHandRow,
    MovementRepository,
    StockReconciliationRepository,
)

_log = structlog.get_logger("inventory.goods_receipt")
_sale_log = structlog.get_logger("inventory.sale_dispense")

#: How many batches a stock-report page pulls per round-trip — same idea as the
#: audit dashboard's export batch (PROJECT_STATE §7al): bounded memory regardless
#: of how many batches match.
_STOCK_REPORT_BATCH = 500

#: How many times a sale's stock-out is replayed when a concurrent counter takes
#: the units between our read and our write. Three, not one: the first retry is
#: the common case (two tills, last box on the shelf), the third is already a
#: three-way tie. Not unbounded — a bound that never trips is still the thing that
#: keeps a live-lock from becoming a hung event handler.
_SALE_DISPENSE_ATTEMPTS = 3

UowFactory = Callable[[], UnitOfWork]
BatchRepoFactory = Callable[[UnitOfWork, RequestContext], BatchRepository]
MovementRepoFactory = Callable[[UnitOfWork, RequestContext], MovementRepository]
BalanceRepoFactory = Callable[[UnitOfWork, RequestContext], BalanceRepository]
ReconciliationRepoFactory = Callable[[UnitOfWork, RequestContext], StockReconciliationRepository]
CountRepoFactory = Callable[[UnitOfWork, RequestContext], StockCountRepository]
AtLocationRepoFactory = Callable[[UnitOfWork, RequestContext], StockAtLocationRepository]


class InventoryService:
    def __init__(
        self,
        uow_factory: UowFactory,
        batch_repo_factory: BatchRepoFactory,
        movement_repo_factory: MovementRepoFactory,
        balance_repo_factory: BalanceRepoFactory,
        reconciliation_repo_factory: ReconciliationRepoFactory,
        audit: AuditLogger,
        *,
        reorder_point: Decimal = Decimal("0"),
        count_repo_factory: CountRepoFactory | None = None,
        at_location_repo_factory: AtLocationRepoFactory | None = None,
        locations: LocationInfoProvider | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._batches = batch_repo_factory
        self._movements = movement_repo_factory
        self._balances = balance_repo_factory
        self._reconciliations = reconciliation_repo_factory
        self._audit = audit
        self._reorder_point = reorder_point
        # 🔴 Tuỳ chọn, mặc định `None`: mọi bên gọi đang có — kể cả hàng chục test dựng
        # service bằng tay — chạy nguyên vẹn mà không sửa một dòng. Chưa cấu hình thì các
        # use-case vị trí trả rỗng hoặc từ chối tường minh, KHÔNG ném AttributeError.
        self._counts = count_repo_factory
        self._at_location = at_location_repo_factory
        self._locations = locations

    async def receive_stock(self, data: ReceiveStockInput, ctx: RequestContext) -> ReceiptOutput:
        """Receive a batch: create it (or fold into an existing same-lot batch — PA B),
        append an IN movement, project the balance.

        Emits :class:`StockMovedIn` after commit. Raises :class:`ValidationError` if
        the received quantity is not strictly positive, or if ``(drug_id, branch_id,
        lot_no)`` already exists with a **different** expiry date (a same lot number
        must carry the same expiry — a mismatch is a data-entry problem, not a
        legitimate re-delivery, so it is never merged nor silently duplicated).
        """
        require_permission(ctx, "inventory.receive")
        if data.quantity <= 0:
            raise ValidationError("Số lượng nhập phải > 0")

        async with self._uow_factory() as uow:
            batches = self._batches(uow, ctx)
            movements = self._movements(uow, ctx)
            balances = self._balances(uow, ctx)

            existing = await batches.find_by_lot(data.drug_id, ctx.branch_id, data.lot_no)
            if existing is not None:
                try:
                    existing.ensure_mergeable_expiry(data.expiry_date)
                except LotExpiryMismatchError as exc:
                    raise ValidationError(str(exc)) from exc
                existing.merge_receipt(data.quantity, data.cost_price)
                await batches.update(existing)
                batch = existing
            else:
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
                await batches.add(batch)

            await movements.add(
                StockMovement(
                    drug_id=batch.drug_id,
                    batch_id=batch.id,
                    branch_id=ctx.branch_id,
                    tenant_id=ctx.tenant_id,
                    type=MovementType.IN,
                    quantity=data.quantity,
                    # `IN` chứ không phải một loại chuyển động mới: hiệu ứng lên tồn kho
                    # giống hệt nhau, và thêm một loại vào enum sẽ buộc mọi chỗ đang phân
                    # nhánh theo `type` phải biết về nó. Cái khác nhau là Ý NGHĨA, và ý
                    # nghĩa thuộc về `ref_type`.
                    ref_type="INIT" if data.is_initial else "GRN",
                )
            )
            await balances.adjust(
                batch.drug_id, batch.id, ctx.branch_id, ctx.tenant_id, data.quantity
            )
            # 🔴 Cất thẳng vào ô trong CÙNG một giao dịch với lượt nhận (Phase 5).
            #
            # Tách làm hai lượt gọi như trước sẽ để lại một khoảng — có thể vài phút, có
            # thể vài ngày — mà hàng đã nằm trong sổ tồn nhưng chưa có địa chỉ. Người ra
            # quầy trong khoảng đó được bảo "chưa xếp ô", dù hàng đang nằm ngay trên kệ.
            #
            # Dùng lại đúng `ensure_can_put_away` của Phase 2, không viết quy tắc thứ hai:
            # bất biến hai sổ phải giống hệt nhau dù hàng vào bằng đường nào.
            if data.location_id is not None and self._at_location is not None:
                if self._locations is None:
                    raise ValidationError("Chưa bật tính năng vị trí lưu trữ")
                o = await self._locations.get(data.location_id, ctx.tenant_id, ctx.branch_id)
                if o is None:
                    raise NotFoundError(f"Không tìm thấy vị trí {data.location_id}")
                at_loc = self._at_location(uow, ctx)
                try:
                    ensure_can_put_away(
                        dang_xep=await at_loc.total_for_batch(batch.id),
                        ton_cua_lo=await balances.for_batch(batch.id),
                        them=data.quantity,
                        o_dang_hoat_dong=o.is_active,
                    )
                except PutAwayError as exc:
                    raise ValidationError(str(exc)) from exc
                await at_loc.put_away(
                    drug_id=batch.drug_id,
                    batch_id=batch.id,
                    location_id=data.location_id,
                    delta=data.quantity,
                )
                await movements.add(
                    StockMovement(
                        drug_id=batch.drug_id,
                        batch_id=batch.id,
                        branch_id=ctx.branch_id,
                        tenant_id=ctx.tenant_id,
                        type=MovementType.TRANSFER,
                        quantity=data.quantity,
                        ref_type="PUTAWAY",
                        to_location_id=data.location_id,
                    )
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

        await self._record(ctx, AuditAction.INVENTORY_STOCK_RECEIVED, "batch", batch.id)
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
        case the whole transaction rolls back untouched. "Insufficient" includes
        *stock that was there when we read it and gone by the time we wrote*: the
        counter that loses that race is refused rather than allowed to push the
        batch negative (audit B-04).
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
            # The allocation and the writes share one ``except``: the FEFO plan can
            # be refused up front (stock was already short when read) or at the
            # write (another counter took the same units in between). Same answer to
            # the caller either way — 409, nothing written.
            try:
                allocations = allocate_fefo(avail, data.quantity)
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
            except (InsufficientStockError, DuplicateMovementError) as exc:
                raise ConflictError(str(exc)) from exc

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

        await self._record(ctx, AuditAction.INVENTORY_STOCK_DISPENSED, "drug", data.drug_id)
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

        **Under concurrency both of those promises need a retry, not just a
        check.** Two counters selling the last units at once each read "10 left",
        each think they are within stock, and the loser's write is refused by
        :meth:`BalanceRepository.adjust`. Aborting there would be the worst of both
        worlds: the sale stands, the goods leave, and *nothing* records the gap —
        the "no reconciliation trail" half of audit B-04, which is worse than a
        wrong number because a wrong number at least shows up at stocktake. So the
        transaction is rolled back and replayed against what is *now* on the shelf;
        the second pass takes what is left and raises the shortfall event for the
        remainder. Bounded by :data:`_SALE_DISPENSE_ATTEMPTS` — each pass sees a
        strictly smaller availability, so it converges; the bound only stops a
        pathological live-lock.
        """
        require_permission(ctx, "inventory.dispense")
        for attempt in range(1, _SALE_DISPENSE_ATTEMPTS + 1):
            try:
                await self._dispense_sale_once(items, order_id, ctx)
                return
            except DuplicateMovementError:
                # Another delivery of this same sale got there first — the unique
                # index caught what ``exists_for_ref`` structurally cannot. This is
                # success, not failure: the stock has moved, exactly once.
                _sale_log.info("sale_dispense_already_done", order_id=str(order_id))
                return
            except InsufficientStockError:
                _sale_log.info(
                    "sale_dispense_retry", order_id=str(order_id), attempt=attempt
                )  # stock moved under us; re-read and re-allocate
        raise ConflictError(
            f"Không xuất được kho cho đơn {order_id} sau {_SALE_DISPENSE_ATTEMPTS} lần thử"
        )

    async def _dispense_sale_once(
        self, items: list[SaleDispenseItem], order_id: UUID, ctx: RequestContext
    ) -> None:
        """One transactional attempt of :meth:`dispense_for_sale` — all or nothing."""
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
        """React to a confirmed goods-receipt note: create one batch per line (or
        fold into an existing same-lot batch — PA B, same rule as manual receive).

        Idempotent on ``grn_id`` (skips entirely if this GRN's stock-in already
        ran — every IN movement it writes carries ``ref_type="grn"``,
        ``ref_id=grn_id``, and ``uq_movement_ref_batch`` enforces that even when two
        deliveries of the event race). A line whose ``(drug_id, branch_id, lot_no)`` already
        exists **and matches expiry** is merged (:meth:`ProductBatch.merge_receipt`);
        a mismatch is **skipped, not merged** and flagged in
        ``stock_reconciliation_needed`` — a confirmed GRN can't be interactively
        corrected, so a genuine data anomaly still needs a human to look at it. Any
        unexpected failure aborts the whole transaction and is likewise flagged
        best-effort in a fresh transaction — the GRN is already confirmed, so a
        silent stock gap is never left behind.
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

                # Stock-in accumulated per BATCH, written after the loop. Two lines
                # of one GRN can legitimately fold into the same batch (same drug +
                # lot + expiry, e.g. two PO items of one delivery), and
                # ``uq_movement_ref_batch`` allows exactly one movement per
                # ``(grn, batch)`` — that key is what makes replay safety hold, so
                # the receipt bends around it rather than the other way round.
                # Nothing is lost by summing: a GRN movement carries no
                # ``po_item_id``, so per-line rows were already indistinguishable,
                # and the per-line ``StockMovedIn`` events below still go out one by
                # one.
                stock_in: dict[UUID, tuple[UUID, Decimal]] = {}

                for line in lines:
                    if line.quantity <= 0:
                        continue
                    existing = await batches.find_by_lot(line.drug_id, ctx.branch_id, line.lot_no)
                    if existing is not None:
                        try:
                            existing.ensure_mergeable_expiry(line.expiry_date)
                        except LotExpiryMismatchError:
                            await reconciliations.add(
                                StockReconciliationNeeded(
                                    tenant_id=ctx.tenant_id,
                                    branch_id=ctx.branch_id,
                                    grn_id=grn_id,
                                    po_item_id=line.po_item_id,
                                    reason=(
                                        f"lot_collision: drug={line.drug_id} lot={line.lot_no} "
                                        f"trùng lô đã có (batch {existing.id}) nhưng khác HSD; "
                                        f"bỏ qua, không gộp"
                                    ),
                                )
                            )
                            continue
                        existing.merge_receipt(line.quantity, line.unit_cost)
                        await batches.update(existing)
                        batch = existing
                    else:
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

                    _, received_so_far = stock_in.get(batch.id, (line.drug_id, Decimal("0")))
                    stock_in[batch.id] = (line.drug_id, received_so_far + line.quantity)
                    uow.collect(
                        StockMovedIn(
                            tenant_id=ctx.tenant_id,
                            drug_id=line.drug_id,
                            batch_id=batch.id,
                            branch_id=ctx.branch_id,
                            quantity=line.quantity,
                        )
                    )

                for batch_id, (drug_id, quantity) in stock_in.items():
                    await movements.add(
                        StockMovement(
                            drug_id=drug_id,
                            batch_id=batch_id,
                            branch_id=ctx.branch_id,
                            tenant_id=ctx.tenant_id,
                            type=MovementType.IN,
                            quantity=quantity,
                            ref_type="grn",
                            ref_id=grn_id,
                        )
                    )
                    await balances.adjust(drug_id, batch_id, ctx.branch_id, ctx.tenant_id, quantity)
                await uow.commit()
        except DuplicateMovementError:
            # Concurrent redelivery of the same GoodsReceived: the other one landed
            # the stock. Idempotent success — not an anomaly, so no reconciliation
            # flag and nothing for a human to look at.
            _log.info("grn_stock_in_already_done", grn_id=str(grn_id))
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

    async def on_hand_by_drug(
        self, ctx: RequestContext, *, branch_id: UUID | None = None
    ) -> list[DrugOnHandRow]:
        """On-hand per drug (all drugs with positive stock) at *branch_id*, defaulting
        to the caller's branch. Bulk read for the analytics reorder run — see
        :class:`DrugOnHandRow`. Requires ``inventory.read``."""
        require_permission(ctx, "inventory.read")
        target = branch_id if branch_id is not None else ctx.branch_id
        async with self._uow_factory() as uow:
            balances = self._balances(uow, ctx)
            return await balances.on_hand_by_drug(target)

    async def list_stock(
        self,
        ctx: RequestContext,
        *,
        branch_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StockReportItem]:
        """Một trang tồn kho theo lô, **cận hạn lên trước** (Sprint 10, D3).

        Cùng nguồn dữ liệu với :meth:`stock_report_rows` nhưng **không** stream:
        báo cáo xuất khẩu đọc hết mọi lô nên phải chảy theo dòng, còn màn hình đọc
        50 dòng một lần và cần biết mình đang ở trang nào. Trộn hai nhu cầu vào một
        hàm sẽ bắt màn hình phải tiêu hoá một AsyncIterator để lấy đúng một trang.

        Thứ tự cận-hạn-trước là quyết định nghiệp vụ chứ không phải mặc định kỹ
        thuật: lô sắp hết hạn là lô phải bán hoặc trả trước, nên nó thuộc về đầu
        danh sách kể cả khi người dùng chưa lọc gì.

        Đòi ``inventory.read`` — không thêm quyền mới. Trả về **id thuốc**, không
        kèm tên: inventory không được import catalog (contract import-linter), và
        màn hình đã cần ``GET /drugs`` cho ô tìm kiếm của nó nên gắn tên ở phía
        client bằng ``?ids=`` là một lượt gọi, không phải N.
        """
        require_permission(ctx, "inventory.read")
        async with self._uow_factory() as uow:
            batches = self._batches(uow, ctx)
            page = await batches.stock_report(
                ctx.tenant_id, branch_id=branch_id, limit=limit, offset=offset
            )
        return [
            StockReportItem(
                batch_id=row.batch_id,
                drug_id=row.drug_id,
                branch_id=row.branch_id,
                lot_no=row.lot_no,
                expiry_date=row.expiry_date,
                quantity=row.quantity,
            )
            for row in page
        ]

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

    async def list_reconciliations(
        self,
        ctx: RequestContext,
        *,
        resolved: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReconciliationOutput]:
        """List the caller branch's stock-reconciliation flags, newest first."""
        require_permission(ctx, "inventory.reconcile")
        async with self._uow_factory() as uow:
            reconciliations = self._reconciliations(uow, ctx)
            found = await reconciliations.list(
                ctx.tenant_id, ctx.branch_id, resolved=resolved, limit=limit, offset=offset
            )
        return [ReconciliationOutput.of(r) for r in found]

    async def resolve_reconciliation(
        self, reconciliation_id: UUID, ctx: RequestContext
    ) -> ReconciliationOutput:
        """Mark a stock-reconciliation flag as handled.

        404 if unknown for the tenant; 409 if already resolved. Who/when is the
        audit trail's job (:class:`AuditAction.INVENTORY_RECONCILIATION_RESOLVED`),
        not a new column on the record itself.
        """
        require_permission(ctx, "inventory.reconcile")
        async with self._uow_factory() as uow:
            reconciliations = self._reconciliations(uow, ctx)
            record = await reconciliations.get(reconciliation_id, ctx.tenant_id)
            if record is None:
                raise NotFoundError(f"Không tìm thấy mục đối soát {reconciliation_id}")
            try:
                record.resolve()
            except ReconciliationAlreadyResolvedError as exc:
                raise ConflictError(str(exc)) from exc
            await reconciliations.update(record)
            await uow.commit()

        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=AuditAction.INVENTORY_RECONCILIATION_RESOLVED,
                target_type="stock_reconciliation_needed",
                target_id=str(record.id),
            ).with_context(**ctx.audit_meta, branch_id=str(ctx.branch_id))
        )
        return ReconciliationOutput.of(record)

    async def _record(
        self,
        ctx: RequestContext,
        action: AuditAction,
        target_type: str,
        target_id: UUID,
        **extra: str,
    ) -> None:
        """Append one audit row — metadata only, never cost price/lot content.

        ``extra`` chỉ nhận **số đếm, mã, lý do do người gõ** — không nhận nội dung lô hay
        giá vốn, cùng kỷ luật đã ghi ở :attr:`AuditAction.CATALOG_DRUG_INGREDIENTS_REPLACED`.
        Thêm 2026-08-01 cho đường điều chỉnh tồn nhanh (M-07): nó cần mang ``old_qty`` /
        ``new_qty`` / ``reason``, và sổ audit là chỗ **duy nhất** trả lời được *"vì sao tồn
        của lô này đổi"* — bảng ``stock_movements`` chỉ ghi rằng nó đã đổi.
        """
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type=target_type,
                target_id=str(target_id),
            ).with_context(**ctx.audit_meta, branch_id=str(ctx.branch_id), **extra)
        )

    async def stock_report_rows(
        self, ctx: RequestContext, *, branch_id: UUID | None = None
    ) -> AsyncIterator[StockReportItem]:
        """Current on-hand by lot + expiry — Sprint 7 stock report (PROJECT_STATE
        §7am/§7an), soonest-expiring first.

        Requires ``inventory.read`` (reused — no new permission). Checked eagerly
        so a caller lacking it 403s before any streaming begins — same split as
        :class:`AuditDashboardService.export_rows`. Tenant-wide by default
        (``branch_id`` narrows to one branch): a deliberate widening from the
        single-branch scope of :meth:`on_hand`/:meth:`list_near_expiry`, because
        this is a chain-level report surface, not an operational read bound to the
        caller's own session branch (documented, PROJECT_STATE §7an).

        Paged in batches of :data:`_STOCK_REPORT_BATCH` (one DB round-trip per
        batch, held on a single connection for the stream's lifetime) so memory
        stays flat regardless of how many batches match.
        """
        require_permission(ctx, "inventory.read")
        return self._stock_report_stream(ctx, branch_id=branch_id)

    async def _stock_report_stream(
        self, ctx: RequestContext, *, branch_id: UUID | None
    ) -> AsyncIterator[StockReportItem]:
        offset = 0
        async with self._uow_factory() as uow:
            batches = self._batches(uow, ctx)
            while True:
                page = await batches.stock_report(
                    ctx.tenant_id,
                    branch_id=branch_id,
                    limit=_STOCK_REPORT_BATCH,
                    offset=offset,
                )
                for row in page:
                    yield StockReportItem(
                        batch_id=row.batch_id,
                        drug_id=row.drug_id,
                        branch_id=row.branch_id,
                        lot_no=row.lot_no,
                        expiry_date=row.expiry_date,
                        quantity=row.quantity,
                    )
                if len(page) < _STOCK_REPORT_BATCH:
                    return
                offset += _STOCK_REPORT_BATCH

    async def cogs_by_order(
        self, order_ids: Sequence[UUID], ctx: RequestContext
    ) -> dict[UUID, Decimal]:
        """Cost of goods sold per sale order, for the profit report (ROADMAP V3-7a).

        Sums ``StockMovement`` rows this drug's FEFO dispense wrote for each order
        (``ref_type="sale"``, ``ref_id=order_id`` — see
        :meth:`dispense_for_sale`/:meth:`_dispense_sale_once`), valued at each
        movement's batch's **current** ``cost_price``. See
        :meth:`~pharmacy_os.modules.inventory.domain.ports.MovementRepository.cost_by_ref`
        for why that is an approximation, not a point-in-time snapshot.

        Deliberately **gross**, matching :meth:`SalesService.revenue_report_rows`'s
        own policy (counts a sale's full value even if later returned) — a return
        does not reverse the original dispense's ``StockMovement`` row, so this
        method's total already stays gross without special-casing returns. Profit
        computed as revenue − this must use the *same* policy on both sides or the
        two numbers would not be comparable.

        Requires ``inventory.read`` (reused — this is not more sensitive than what
        the stock report already reads about the same batches, PROJECT_STATE §7dt/
        §7dv). An ``order_id`` with nothing dispensed for it (e.g. an order that
        predates :meth:`dispense_for_sale` being wired, or a fully-out-of-stock
        line) is **absent** from the result, same convention as
        :meth:`CatalogService.drug_names`.
        """
        require_permission(ctx, "inventory.read")
        async with self._uow_factory() as uow:
            movements = self._movements(uow, ctx)
            return await movements.cost_by_ref("sale", order_ids)

    # ── BERAS V2 Phase 2: tồn theo vị trí ─────────────────────────────────────────

    async def put_away(
        self,
        *,
        batch_id: UUID,
        location_id: UUID,
        quantity: Decimal,
        ctx: RequestContext,
    ) -> PutAwayOutput:
        """Cất hàng của một lô vào một ô.

        Không tạo hàng mới: hàng đã tồn tại trong ``stock_balances`` từ lúc nhận. Việc này
        chỉ **nói ra nó đang nằm đâu** — nên nó ghi một ``StockMovement`` loại ``TRANSFER``
        với ``to_location_id``, và ``TRANSFER`` cố ý **không đổi tổng tồn** (xem
        ``StockMovement.signed_quantity``: chỉ ``OUT`` mới âm).

        Quyền ``inventory.receive`` — cất hàng lên kệ là việc của người nhận hàng, cùng một
        đôi tay. Không tạo quyền mới cho một thao tác thuộc cùng một công việc.

        Raises :class:`NotFoundError` nếu lô hoặc ô không thuộc chi nhánh;
        :class:`ValidationError` nếu ô đã ngừng hoạt động hoặc xếp vượt tồn của lô.
        """
        require_permission(ctx, "inventory.receive")
        if self._locations is None or self._at_location is None:
            raise ValidationError("Chưa bật tính năng vị trí lưu trữ")

        o = await self._locations.get(location_id, ctx.tenant_id, ctx.branch_id)
        if o is None:
            raise NotFoundError(f"Không tìm thấy vị trí {location_id}")

        async with self._uow_factory() as uow:
            batches = self._batches(uow, ctx)
            lo = await batches.get(batch_id)
            if lo is None:
                raise NotFoundError(f"Không tìm thấy lô {batch_id}")

            balances = self._balances(uow, ctx)
            ton_cua_lo = await balances.for_batch(batch_id)
            at_loc = self._at_location(uow, ctx)
            dang_xep = await at_loc.total_for_batch(batch_id)

            try:
                ensure_can_put_away(
                    dang_xep=dang_xep,
                    ton_cua_lo=ton_cua_lo,
                    them=quantity,
                    o_dang_hoat_dong=o.is_active,
                )
            except PutAwayError as exc:
                raise ValidationError(str(exc)) from exc

            await at_loc.put_away(
                drug_id=lo.drug_id, batch_id=batch_id, location_id=location_id, delta=quantity
            )
            movements = self._movements(uow, ctx)
            await movements.add(
                StockMovement(
                    drug_id=lo.drug_id,
                    batch_id=batch_id,
                    branch_id=ctx.branch_id,
                    tenant_id=ctx.tenant_id,
                    type=MovementType.TRANSFER,
                    quantity=quantity,
                    ref_type="PUTAWAY",
                    to_location_id=location_id,
                )
            )
            await uow.commit()

        await self._record_putaway(ctx, batch_id, o.path, quantity)
        return PutAwayOutput(
            batch_id=batch_id,
            location_id=location_id,
            location_path=o.path,
            quantity=quantity,
            chua_xep_o=chua_xep_o(ton_cua_lo=ton_cua_lo, dang_xep=dang_xep + quantity),
        )

    async def where_is(self, drug_id: UUID, ctx: RequestContext) -> list[PickCandidate]:
        """Thuốc này đang nằm ở những ô nào — **đã sắp theo thứ tự lấy hàng**.

        Sắp ngay ở đây chứ không để màn hình tự sắp: FEFO là quy tắc **nghiệp vụ**, và mỗi
        màn hình tự sắp lấy là mỗi màn hình có cơ hội sắp sai một kiểu khác nhau.

        Quyền ``inventory.read`` — ai đứng quầy cũng cần biết đi lấy ở đâu.
        """
        require_permission(ctx, "inventory.read")
        if self._locations is None or self._at_location is None:
            return []

        async with self._uow_factory() as uow:
            rows = await self._at_location(uow, ctx).rows_for_drug(drug_id)
        if not rows:
            return []

        info = await self._locations.many(
            frozenset(r.location_id for r in rows), ctx.tenant_id, ctx.branch_id
        )
        ung_vien = [
            PickCandidate(
                location_id=r.location_id,
                location_path=info[r.location_id].path,
                pick_order=info[r.location_id].pick_order,
                batch_id=r.batch_id,
                lot_no=r.lot_no,
                expiry_date=r.expiry_date,
                quantity=r.quantity,
            )
            for r in rows
            if r.location_id in info
        ]
        return sort_pick_candidates(ung_vien)

    async def lo_trinh_lay_hang(
        self, yeu_cau: list[tuple[UUID, Decimal]], ctx: RequestContext
    ) -> tuple[list[ChangLay], list[UUID]]:
        """Lộ trình đi lấy hàng cho **cả giỏ** (BERAS V2 Phase 4).

        Vào: ``[(drug_id, số lượng cần)]``. Ra: ``(các chặng đã gộp theo ô, mã thiếu hàng)``.

        🔴 **Không ném lỗi khi thiếu.** Một giỏ mười mã mà một mã chưa xếp ô thì người đi lấy
        vẫn cần chín mã kia — trả về lộ trình cho cái lấy được và **nói ra** cái không lấy
        được, chứ không bỏ trắng cả tờ. Đây là khác biệt với `allocate_from_locations`, vốn
        ném `InsufficientStockError` vì nó phục vụ một lượt xuất kho phải toàn-vẹn-hoặc-không.

        Thiếu ở đây **không** đồng nghĩa kho hết hàng — có thể hàng còn nhưng chưa ai xếp vào
        ô. Màn hình phải nói ra sự khác biệt đó, y như `where_is`.

        Quyền ``inventory.read``: ai đứng quầy cũng cần biết đi lấy ở đâu.
        """
        require_permission(ctx, "inventory.read")
        phan_bo: list[tuple[UUID, list[tuple[PickCandidate, Decimal]]]] = []
        thieu: list[UUID] = []
        for drug_id, can in yeu_cau:
            if can <= 0:
                continue
            ung_vien = await self.where_is(drug_id, ctx)
            try:
                phan_bo.append((drug_id, allocate_from_locations(ung_vien, can)))
            except (InsufficientStockError, ValueError):
                thieu.append(drug_id)
        return gom_lo_trinh(phan_bo), thieu

    async def tom_tat_moi_o(self, ctx: RequestContext) -> list[TomTatO]:
        """Tóm tắt tồn của **mọi ô đang giữ hàng** — nguồn của sơ đồ trực quan (Phase 12).

        Chỉ ô **có hàng** mới có dòng. Màn hình biết ô nào trống bằng cách đối chiếu với sơ
        đồ (`GET /locations`) — *"không có dòng"* rẻ hơn *"dòng với số 0"* cho một kho mà
        phần lớn ô trống.

        Quyền ``inventory.read``.
        """
        require_permission(ctx, "inventory.read")
        if self._at_location is None:
            return []
        async with self._uow_factory() as uow:
            return list(await self._at_location(uow, ctx).tom_tat_moi_o())

    async def stock_at_location(
        self, location_id: UUID, ctx: RequestContext
    ) -> list[LocationStockRow]:
        """Ô này đang giữ những lô nào — nguồn của câu *"ô A01 có thuốc gì"*."""
        require_permission(ctx, "inventory.read")
        if self._at_location is None:
            return []
        async with self._uow_factory() as uow:
            return list(await self._at_location(uow, ctx).rows_at_location(location_id))

    async def _record_putaway(
        self, ctx: RequestContext, batch_id: UUID, path: str, quantity: Decimal
    ) -> None:
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=AuditAction.INVENTORY_PUT_AWAY,
                target_type="batch",
                target_id=str(batch_id),
            ).with_context(
                **ctx.audit_meta,
                branch_id=str(ctx.branch_id),
                location_path=path,
                quantity=str(quantity),
            )
        )

    # ── BERAS V2 Phase 11: kiểm kê theo ô ────────────────────────────────────────

    def _count_repo(self, uow: UnitOfWork, ctx: RequestContext) -> StockCountRepository:
        """Cổng vào duy nhất tới sổ kiểm kê — ném lỗi rõ nếu tính năng chưa nối dây.

        Cùng khuôn với ``put_away``: bộ test cũ dựng ``InventoryService`` không có kho lẫn
        kiểm kê, và một ``AttributeError`` ở giữa giao dịch khó đọc hơn nhiều một câu tiếng
        Việt nói thẳng.
        """
        if self._counts is None:
            raise ValidationError("Chưa bật tính năng kiểm kê")
        return self._counts(uow, ctx)

    async def open_count(self, location_id: UUID, ctx: RequestContext) -> StockCount:
        """Mở một phiên kiểm kê cho một ô. Quyền ``inventory.receive``.

        Không chặn hai phiên cùng mở trên một ô. Hai người đếm song song cùng một ô là dấu
        hiệu tổ chức công việc lộn xộn, không phải một lỗi dữ liệu — và cả hai phiên đều
        phải qua duyệt trước khi đụng tồn kho, nên hậu quả xấu nhất là người duyệt thấy hai
        phiếu và từ chối một. Chặn ở đây sẽ đổi lấy một trạng thái kẹt: một phiên bỏ dở
        khoá vĩnh viễn cái ô.
        """
        require_permission(ctx, "inventory.receive")
        if self._locations is None:
            raise ValidationError("Chưa bật tính năng vị trí lưu trữ")
        o = await self._locations.get(location_id, ctx.tenant_id, ctx.branch_id)
        if o is None:
            raise NotFoundError(f"Không tìm thấy vị trí {location_id}")

        phien = StockCount(
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            location_id=location_id,
            counted_by=ctx.user_id,
        )
        async with self._uow_factory() as uow:
            await self._count_repo(uow, ctx).add(phien)
            await uow.commit()
        return phien

    async def count_line(
        self, count_id: UUID, batch_id: UUID, counted_qty: Decimal, ctx: RequestContext
    ) -> StockCount:
        """Ghi số đếm được của một lô. Quyền ``inventory.receive``."""
        require_permission(ctx, "inventory.receive")
        async with self._uow_factory() as uow:
            repo = self._count_repo(uow, ctx)
            phien = await repo.get(count_id)
            if phien is None:
                raise NotFoundError(f"Không tìm thấy phiên kiểm kê {count_id}")
            try:
                phien.dem(batch_id, counted_qty)
            except CountError as exc:
                raise ConflictError(str(exc)) from exc
            await repo.update(phien)
            await uow.commit()
        return phien

    async def submit_count(self, count_id: UUID, ctx: RequestContext) -> StockCount:
        """Nộp phiên: đọc sổ vị trí **tại đúng lúc này** rồi chốt vào từng dòng.

        🔴 Đọc ``stock_at_location`` chứ không ``stock_balances``: phiên kiểm kê một ô, và
        câu hỏi là *"ô này đang ghi bao nhiêu"*, không phải *"cả chi nhánh có bao nhiêu"*.
        Lấy nhầm sổ sẽ khiến mọi lô nằm ở nhiều ô đều báo thiếu.
        """
        require_permission(ctx, "inventory.receive")
        async with self._uow_factory() as uow:
            repo = self._count_repo(uow, ctx)
            phien = await repo.get(count_id)
            if phien is None:
                raise NotFoundError(f"Không tìm thấy phiên kiểm kê {count_id}")
            if self._at_location is None:
                raise ValidationError("Chưa bật tính năng vị trí lưu trữ")

            dong_o = await self._at_location(uow, ctx).rows_at_location(phien.location_id)
            so_ghi = {r.batch_id: r.quantity for r in dong_o}
            try:
                phien.submit(so_ghi=so_ghi)
            except CountError as exc:
                raise ConflictError(str(exc)) from exc
            await repo.update(phien)
            await uow.commit()
        return phien

    async def approve_count(
        self, count_id: UUID, ctx: RequestContext, **audit_extra: str
    ) -> StockCount:
        """Duyệt phiên và **áp chênh lệch vào cả hai sổ**. Quyền ``inventory.reconcile``.

        Ba thứ phải đi cùng một giao dịch, nếu không sổ sẽ lệch nhau:
          1. ``stock_balances``    — tồn tổng của lô
          2. ``stock_at_location`` — tồn tại ô đang kiểm
          3. một ``StockMovement`` loại ``ADJUST`` cho mỗi dòng chênh

        Mục 3 là chỗ ``MovementType.ADJUST`` được dùng **lần đầu** kể từ commit đầu tiên của
        dự án. ``ref_type='COUNT'`` để phân biệt với mọi nguồn điều chỉnh về sau.
        """
        require_permission(ctx, "inventory.reconcile")
        async with self._uow_factory() as uow:
            repo = self._count_repo(uow, ctx)
            phien = await repo.get(count_id)
            if phien is None:
                raise NotFoundError(f"Không tìm thấy phiên kiểm kê {count_id}")
            if self._at_location is None:
                raise ValidationError("Chưa bật tính năng vị trí lưu trữ")

            try:
                lech = phien.approve(by=ctx.user_id)
            except CountError as exc:
                raise ConflictError(str(exc)) from exc

            batches = self._batches(uow, ctx)
            balances = self._balances(uow, ctx)
            at_loc = self._at_location(uow, ctx)
            movements = self._movements(uow, ctx)

            for dong in lech:
                delta = dong.lech
                if delta is None:  # pragma: no cover - approve() đã lọc dòng chưa chốt
                    continue
                lo = await batches.get(dong.batch_id)
                if lo is None:
                    raise NotFoundError(f"Không tìm thấy lô {dong.batch_id}")
                await balances.adjust(
                    lo.drug_id, dong.batch_id, ctx.branch_id, ctx.tenant_id, delta
                )
                await at_loc.put_away(
                    drug_id=lo.drug_id,
                    batch_id=dong.batch_id,
                    location_id=phien.location_id,
                    delta=delta,
                )
                await movements.add(
                    StockMovement(
                        drug_id=lo.drug_id,
                        batch_id=dong.batch_id,
                        branch_id=ctx.branch_id,
                        tenant_id=ctx.tenant_id,
                        type=MovementType.ADJUST,
                        quantity=delta,
                        ref_type="COUNT",
                        ref_id=phien.id,
                        to_location_id=phien.location_id,
                    )
                )
            await repo.update(phien)
            await uow.commit()

        await self._record(
            ctx, AuditAction.INVENTORY_COUNT_APPROVED, "stock_count", phien.id, **audit_extra
        )
        return phien

    async def adjust_stock_at_location(
        self,
        *,
        location_id: UUID,
        batch_id: UUID,
        actual_qty: Decimal,
        reason: str,
        ctx: RequestContext,
    ) -> StockCount:
        """Điều chỉnh tồn **một lô tại một ô** trong một lượt (UAT lỗi M-07, 2026-08-01).

        🔴 **Không phải một đường đổi tồn kho mới.** Nó chạy trọn vẹn luồng kiểm kê đã có —
        mở phiên → ghi số đếm → nộp → duyệt — chỉ gộp bốn lượt bấm thành một. Lý do gắt:

        * ``approve_count`` phải cập nhật **cả ba** sổ trong cùng một giao dịch —
          ``stock_balances``, ``stock_at_location``, và một ``StockMovement`` loại ``ADJUST``.
          Một đường tắt sửa thẳng ``stock_balances`` sẽ làm hai sổ lệch nhau **im lặng**, và
          chỉ lộ ra khi có người đứng trước một ô rỗng.
        * Đúng một đường đổi tồn nghĩa là đúng một chỗ phải canh, và mọi lượt điều chỉnh đều
          để lại một phiếu kiểm kê tra được — thứ thanh tra hỏi khi tồn sổ khác tồn thực.

        Vẫn giữ **tách quyền**: mở/ghi số cần ``inventory.receive``, duyệt cần
        ``inventory.reconcile``. Ai chỉ có quyền đếm mà không có quyền duyệt sẽ dừng ở bước
        cuối với 403 — đúng như đi đường dài, không có ưu ái nào cho đường tắt.

        ``reason`` **bắt buộc**, và đi vào ``context`` của dòng audit chứ không vào một cột
        mới: sổ audit là chỗ duy nhất trả lời được *"vì sao tồn của lô này đổi"* —
        ``stock_movements`` chỉ ghi rằng nó đã đổi. Kèm ``old_qty``/``new_qty`` để màn Nhật
        ký hiện thẳng "cũ → mới" (M-05) mà không phải mở thêm màn nào.

        ⚠️ Bốn bước **không nằm chung một giao dịch**. Hỏng giữa chừng để lại một phiên kiểm
        kê dở dang — nó **hiện ra ở màn Kiểm kê** để người ta xử tiếp, chứ không phải một sổ
        lệch âm thầm. Đây là đánh đổi có chủ đích: thà một phiếu treo nhìn thấy được còn hơn
        một con số sai không ai biết.
        """
        if not reason.strip():
            raise ValidationError("Điều chỉnh tồn phải ghi lý do")
        if actual_qty < 0:
            raise ValidationError("Số thực tế không thể âm")

        phien = await self.open_count(location_id, ctx)
        await self.count_line(phien.id, batch_id, actual_qty, ctx)
        da_nop = await self.submit_count(phien.id, ctx)

        # Số sổ ĐANG ghi, chốt tại lúc nộp — đọc từ chính phiên vừa nộp thay vì hỏi lại sổ,
        # để con số ghi vào audit đúng là con số mà phép so sánh đã dùng.
        dong = next((d for d in da_nop.lines if d.batch_id == batch_id), None)
        so_cu = "?" if dong is None or dong.system_qty is None else str(dong.system_qty)

        # 🔴 Ngữ cảnh đi KÈM lời gọi duyệt, không phải một dòng audit thứ hai. Bản đầu ghi
        # thêm một `_record` riêng và mỗi lượt điều chỉnh để lại **HAI** dòng
        # `INVENTORY_COUNT_APPROVED` cho cùng một việc — một dòng trần, một dòng có lý do.
        # Không cổng nào đỏ (cả hai dòng đều hợp lệ), nhưng người soát sổ đếm gấp đôi số
        # lượt duyệt, và dòng trần đọc như một lượt duyệt KHÔNG có lý do.
        return await self.approve_count(
            phien.id,
            ctx,
            old_qty=so_cu,
            new_qty=str(actual_qty),
            reason=reason.strip()[:500],
            adjust_batch_id=str(batch_id),
        )

    async def reject_count(self, count_id: UUID, ctx: RequestContext) -> StockCount:
        """Từ chối phiên. **Không** đụng tồn kho. Quyền ``inventory.reconcile``."""
        require_permission(ctx, "inventory.reconcile")
        async with self._uow_factory() as uow:
            repo = self._count_repo(uow, ctx)
            phien = await repo.get(count_id)
            if phien is None:
                raise NotFoundError(f"Không tìm thấy phiên kiểm kê {count_id}")
            try:
                phien.reject(by=ctx.user_id)
            except CountError as exc:
                raise ConflictError(str(exc)) from exc
            await repo.update(phien)
            await uow.commit()

        await self._record(ctx, AuditAction.INVENTORY_COUNT_REJECTED, "stock_count", phien.id)
        return phien

    async def get_count(self, count_id: UUID, ctx: RequestContext) -> StockCount:
        """Một phiên kèm dòng. Quyền ``inventory.read``."""
        require_permission(ctx, "inventory.read")
        async with self._uow_factory() as uow:
            phien = await self._count_repo(uow, ctx).get(count_id)
        if phien is None:
            raise NotFoundError(f"Không tìm thấy phiên kiểm kê {count_id}")
        return phien

    async def list_counts(
        self,
        ctx: RequestContext,
        *,
        status: CountStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[StockCount]:
        """Danh sách phiên của chi nhánh, mới nhất trước. Quyền ``inventory.read``."""
        require_permission(ctx, "inventory.read")
        async with self._uow_factory() as uow:
            rows = await self._count_repo(uow, ctx).list(
                status=str(status) if status is not None else None, limit=limit, offset=offset
            )
        return list(rows)
