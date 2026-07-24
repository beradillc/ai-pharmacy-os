"""Sales use-cases: completing an (offline-originated) sale, idempotently.

The service depends only on ports; the concrete repository and unit of work are
injected as factories at composition time (see the module ``register``).

Offline-first idempotency: a sale carries a client-generated ``client_uuid``. If
a sync retries a sale already recorded, :meth:`complete_sale` returns the stored
result **without** re-processing — so no duplicate order and no duplicate
``SaleCompleted`` (which would otherwise double-dispense stock).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.sales.application.dto import (
    CreateSaleInput,
    ReceiptLine,
    ReceiptPayment,
    ReceiptSummaryDTO,
    RegisterReturnInput,
    RevenueGranularity,
    RevenueRow,
    SaleLineInput,
    SaleOutput,
)
from pharmacy_os.modules.sales.domain import (
    Payment,
    SaleCompleted,
    SaleLine,
    SaleReturned,
    SalesError,
    SalesOrder,
    SoldItem,
    ensure_prescription_valid_for_sale,
)
from pharmacy_os.modules.sales.domain.ports import (
    DrugInfoProvider,
    OrderRevenueRow,
    PrescriptionInfoProvider,
    SalesRepository,
)
from pharmacy_os.shared.value_objects import Money

#: How many orders a revenue-report page pulls per round-trip while bucketing —
#: same idea as the audit dashboard's export batch (PROJECT_STATE §7al): bounded
#: memory regardless of how many orders match the date range.
_REVENUE_REPORT_BATCH = 500

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], SalesRepository]


class SalesService:
    def __init__(
        self,
        uow_factory: UowFactory,
        repo_factory: RepoFactory,
        drug_info: DrugInfoProvider | None = None,
        prescription_info: PrescriptionInfoProvider | None = None,
        audit: AuditLogger | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._drug_info = drug_info
        self._prescription_info = prescription_info
        self._audit = audit

    async def complete_sale(self, data: CreateSaleInput, ctx: RequestContext) -> SaleOutput:
        """Record and finalise a sale for the caller's tenant/branch.

        Idempotent on ``data.client_uuid``: a repeated sync returns the existing
        order untouched. On a fresh sale, runs the domain rules (Rx + full
        payment) and emits :class:`SaleCompleted` after commit. Raises
        :class:`ValidationError` on a domain rule violation.

        When a :class:`DrugInfoProvider` is configured, the Rx status of each
        known drug comes authoritatively from catalog — a client cannot mislabel
        an ETC line as OTC to bypass the prescription rule.
        """
        require_permission(ctx, "sales.create")

        order = SalesOrder(
            tenant_id=ctx.tenant_id,
            branch_id=ctx.branch_id,
            client_uuid=data.client_uuid,
            currency=data.currency,
            prescription_ref=data.prescription_ref,
            customer_id=data.customer_id,
            sold_by_user_id=ctx.user_id,
        )
        try:
            for line in data.lines:
                requires_rx = await self._resolve_requires_rx(line, ctx)
                order.add_line(
                    SaleLine(
                        drug_id=line.drug_id,
                        quantity=line.quantity,
                        unit_price=Money(line.unit_price, data.currency),
                        requires_prescription=requires_rx,
                    )
                )
            for payment in data.payments:
                order.add_payment(
                    Payment(method=payment.method, amount=Money(payment.amount, data.currency))
                )
            await self._verify_prescription_ref(order, ctx)
            order.complete()
        except SalesError as exc:
            raise ValidationError(str(exc)) from exc

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            existing = await repo.by_client_uuid(data.client_uuid)
            if existing is not None:
                return SaleOutput.of(existing)  # idempotent replay — do not re-emit

            await repo.add(order)
            uow.collect(
                SaleCompleted(
                    tenant_id=ctx.tenant_id,
                    order_id=order.id,
                    branch_id=ctx.branch_id,
                    client_uuid=order.client_uuid,
                    items=tuple(
                        SoldItem(drug_id=line.drug_id, quantity=line.quantity)
                        for line in order.lines
                    ),
                )
            )
            try:
                await uow.commit()
            except Exception as exc:  # unique(tenant, client_uuid) race → treat as replay
                await uow.rollback()
                replay = await self._by_client_uuid(data.client_uuid, ctx)
                if replay is not None:
                    return replay
                raise ConflictError("Không thể ghi nhận đơn bán") from exc

        await self._record_sale_completed(ctx, order.id)
        return SaleOutput.of(order)

    async def _record_sale_completed(self, ctx: RequestContext, order_id: UUID) -> None:
        """Append one audit row — metadata only, never line items/prices."""
        if self._audit is None:
            return
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=AuditAction.SALE_COMPLETED,
                target_type="sale",
                target_id=str(order_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )

    async def _verify_prescription_ref(self, order: SalesOrder, ctx: RequestContext) -> None:
        """Verify an ETC order's ``prescription_ref`` is a real, sale-authorising Rx.

        No-op unless a :class:`PrescriptionInfoProvider` is wired (else the
        ref-present-only rule in :meth:`SalesOrder.complete` still applies) and the
        order actually has ETC items with a ref. Keeps sales independent of the
        prescription module — the lookup goes through the injected read-port.
        """
        if self._prescription_info is None:
            return
        if not order.requires_prescription or order.prescription_ref is None:
            return
        info = await self._prescription_info.get(order.prescription_ref, ctx.tenant_id)
        ensure_prescription_valid_for_sale(info.status if info is not None else None)

    async def _resolve_requires_rx(self, line: SaleLineInput, ctx: RequestContext) -> bool:
        """Authoritative Rx status from catalog when known; else the client's flag."""
        if self._drug_info is None:
            return line.requires_prescription
        info = await self._drug_info.get(line.drug_id, ctx.tenant_id)
        if info is None:
            return line.requires_prescription  # unknown drug — trust the caller
        return info.requires_prescription

    async def get_sale(self, order_id: UUID, ctx: RequestContext) -> SaleOutput:
        """Return one sale by id, scoped to the tenant; 404 if not found."""
        require_permission(ctx, "sales.read")
        order = await self._get_order_or_404(order_id, ctx)
        return SaleOutput.of(order)

    async def register_return(
        self, order_id: UUID, data: RegisterReturnInput, ctx: RequestContext
    ) -> SaleOutput:
        """Record a (partial) return of one line on a completed sale.

        Raises :class:`NotFoundError` if the order doesn't exist for the tenant,
        :class:`ValidationError` on an invalid line/quantity or an order not yet
        completed. Emits :class:`SaleReturned` after commit — **no cross-module
        subscriber restocks inventory from this today**: a returned medicine needs
        a pharmacist to inspect it before it can go back on the shelf, so putting
        it back into sellable stock is a separate, manual ``POST
        /inventory/receive`` decision, not an automatic reaction (see
        PROJECT_STATE for the reasoning).
        """
        require_permission(ctx, "sales.return")
        order = await self._get_order_or_404(order_id, ctx)
        try:
            order.register_return(data.line_id, data.quantity)
        except SalesError as exc:
            raise ValidationError(str(exc)) from exc
        # register_return already validated line_id exists, so this always finds it.
        line = next(ln for ln in order.lines if ln.id == data.line_id)

        return_id = uuid4()
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.update(order)
            uow.collect(
                SaleReturned(
                    tenant_id=ctx.tenant_id,
                    return_id=return_id,
                    order_id=order.id,
                    branch_id=order.branch_id,
                    line_id=data.line_id,
                    drug_id=line.drug_id,
                    quantity=data.quantity,
                )
            )
            await uow.commit()

        await self._record_return_registered(ctx, return_id, order.id)
        return SaleOutput.of(order)

    async def _get_order_or_404(self, order_id: UUID, ctx: RequestContext) -> SalesOrder:
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            order = await repo.get(order_id)
        if order is None:
            raise NotFoundError(f"Không tìm thấy đơn bán {order_id}")
        return order

    async def _record_return_registered(
        self, ctx: RequestContext, return_id: UUID, order_id: UUID
    ) -> None:
        """Append one audit row — metadata only, never line items/prices."""
        if self._audit is None:
            return
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=AuditAction.SALE_RETURN_REGISTERED,
                target_type="sale",
                target_id=str(order_id),
                context={"return_id": str(return_id)},
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )

    async def _by_client_uuid(self, client_uuid: str, ctx: RequestContext) -> SaleOutput | None:
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            order = await repo.by_client_uuid(client_uuid)
        return SaleOutput.of(order) if order is not None else None

    async def get_receipt(self, order_id: UUID, ctx: RequestContext) -> ReceiptSummaryDTO:
        """Build a printable receipt projection for a sale (reuses ``sales.read``).

        Read-only — no new permission, no new mutation, no new persisted data;
        just a different shape of an already-readable sale (S7 In bill, rút gọn
        theo docs/14: không VAT, không chiết khấu — không có trong domain).
        """
        require_permission(ctx, "sales.read")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            order = await repo.get(order_id)
        if order is None:
            raise NotFoundError(f"Không tìm thấy đơn bán {order_id}")

        lines = []
        for line in order.lines:
            name, unit = await self._resolve_drug_display(line.drug_id, ctx)
            lines.append(
                ReceiptLine(
                    drug_id=line.drug_id,
                    name=name,
                    unit=unit,
                    quantity=line.quantity,
                    unit_price=line.unit_price.amount,
                    line_total=line.line_total.amount,
                )
            )
        subtotal = order.subtotal.amount
        paid_total = order.paid_total.amount
        change_amount = paid_total - subtotal if paid_total > subtotal else Decimal("0.00")
        return ReceiptSummaryDTO(
            order_id=order.id,
            tenant_id=order.tenant_id,
            branch_id=order.branch_id,
            created_at=order.created_at,
            client_uuid=order.client_uuid,
            currency=order.currency,
            status=order.status.value,
            lines=lines,
            payments=[
                ReceiptPayment(method=p.method, amount=p.amount.amount) for p in order.payments
            ],
            subtotal=subtotal,
            paid_total=paid_total,
            change_amount=change_amount,
            prescription_ref=order.prescription_ref,
        )

    async def _resolve_drug_display(self, drug_id: UUID, ctx: RequestContext) -> tuple[str, str]:
        """Display name/unit for a receipt line; falls back to the raw id."""
        if self._drug_info is not None:
            info = await self._drug_info.get(drug_id, ctx.tenant_id)
            if info is not None and info.name:
                return info.name, info.unit
        return str(drug_id), ""

    @staticmethod
    def _period_start(when: datetime, granularity: RevenueGranularity) -> date:
        """Bucket a timestamp to its period's first day (local to the stored value —
        the project stores ``created_at`` in UTC throughout, so buckets are UTC days).
        """
        day = when.date()
        if granularity is RevenueGranularity.DAY:
            return day
        if granularity is RevenueGranularity.WEEK:
            return day - timedelta(days=day.weekday())  # Monday of that week
        return day.replace(day=1)  # RevenueGranularity.MONTH

    async def revenue_report_rows(
        self,
        ctx: RequestContext,
        *,
        date_from: date,
        date_to: date,
        granularity: RevenueGranularity = RevenueGranularity.DAY,
        branch_id: UUID | None = None,
        sold_by_user_id: UUID | None = None,
    ) -> AsyncIterator[RevenueRow]:
        """Revenue grouped by period/branch/currency over ``[date_from, date_to]``
        (inclusive both ends), Sprint 7 report (PROJECT_STATE §7am/§7an/§7ao).

        Requires ``sales.read`` (reused — no new permission, this is not more
        sensitive than what the POS UI already shows). Permission and the date
        window are checked **eagerly** so a bad request 422s before any streaming
        begins — same split as :class:`AuditDashboardService.export_rows`.

        Grouping happens in Python, not SQL ``date_trunc`` (Postgres-only, and the
        project keeps queries cross-dialect): the repository is paged in batches of
        :data:`_REVENUE_REPORT_BATCH` orders, each folded into a small in-memory
        accumulator keyed by ``(period, branch, currency)`` — bounded by the number
        of distinct buckets in the window, never by the number of orders, so a
        long/busy range still streams with flat memory on the expensive (row) side.

        ``branch_id`` filters to one branch; omitted, the report spans every branch
        in the tenant (chain-level view, matching how ``sales.read`` already lets
        :meth:`get_sale` read across branches — see PROJECT_STATE §7an).

        ``sold_by_user_id`` filters to one salesperson's sales (Chain duyệt PA (a),
        PROJECT_STATE §7ao); omitted, every salesperson counts. Orders recorded
        before the ``sold_by_user_id`` column existed carry no salesperson, so they
        appear only in the unfiltered (every-salesperson) report — a per-salesperson
        report never sees them, by design.
        """
        require_permission(ctx, "sales.read")
        if date_from > date_to:
            raise ValidationError("Khoảng thời gian không hợp lệ: 'từ' sau 'đến'")
        created_from = datetime.combine(date_from, time.min, tzinfo=UTC)
        created_to = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        return self._revenue_report_stream(
            ctx,
            created_from=created_from,
            created_to=created_to,
            granularity=granularity,
            branch_id=branch_id,
            sold_by_user_id=sold_by_user_id,
        )

    async def _revenue_report_stream(
        self,
        ctx: RequestContext,
        *,
        created_from: datetime,
        created_to: datetime,
        granularity: RevenueGranularity,
        branch_id: UUID | None,
        sold_by_user_id: UUID | None,
    ) -> AsyncIterator[RevenueRow]:
        buckets: dict[tuple[date, UUID, str], tuple[Decimal, int]] = {}
        offset = 0
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            while True:
                batch: list[OrderRevenueRow] = await repo.completed_in_range(
                    ctx.tenant_id,
                    branch_id=branch_id,
                    sold_by_user_id=sold_by_user_id,
                    created_from=created_from,
                    created_to=created_to,
                    limit=_REVENUE_REPORT_BATCH,
                    offset=offset,
                )
                for order in batch:
                    key = (
                        self._period_start(order.created_at, granularity),
                        order.branch_id,
                        order.currency,
                    )
                    prev_total, prev_count = buckets.get(key, (Decimal("0"), 0))
                    buckets[key] = (prev_total + order.subtotal, prev_count + 1)
                if len(batch) < _REVENUE_REPORT_BATCH:
                    break
                offset += _REVENUE_REPORT_BATCH
        for (period_start, b_id, currency), (revenue_total, order_count) in sorted(buckets.items()):
            yield RevenueRow(
                period_start=period_start,
                branch_id=b_id,
                currency=currency,
                order_count=order_count,
                revenue_total=revenue_total,
            )
