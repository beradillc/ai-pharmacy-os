"""Analytics use-cases: reorder-suggestion runs, materialising drafts, dashboard.

The service depends only on ports. The cross-module sources/sink are adapters over
sales/inventory/procurement wired at the composition root, so analytics stays
independent. Reads happen outside the analytics unit of work; only the suggestion
writes run in it (each other module owns its own transaction — there is no
cross-module transaction, same eventual-consistency stance as the event handlers).
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.analytics.application.dto import (
    DashboardOutput,
    MaterializeOutput,
    ReorderRunSummary,
    SuggestionOutput,
    TopDrug,
)
from pharmacy_os.modules.analytics.domain import (
    DraftPoCountSource,
    DraftPoSink,
    DrugNameSource,
    ReorderOutcome,
    ReorderPolicy,
    ReorderSuggestion,
    ReorderSuggestionRepository,
    SalesVelocitySource,
    StockLevelSource,
    SuggestionStatus,
    SupplierSource,
    evaluate_reorder,
)

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], ReorderSuggestionRepository]

#: How many top-selling drugs the dashboard returns.
_TOP_DRUGS = 10


class AnalyticsService:
    def __init__(
        self,
        uow_factory: UowFactory,
        repo_factory: RepoFactory,
        sales_source: SalesVelocitySource,
        stock_source: StockLevelSource,
        supplier_source: SupplierSource,
        draft_po_count_source: DraftPoCountSource,
        draft_po_sink: DraftPoSink,
        drug_name_source: DrugNameSource,
        audit: AuditLogger,
        *,
        window_days: int = 90,
        lead_time_days: int = 7,
        safety_stock_days: int = 3,
        near_expiry_days: int = 90,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._sales = sales_source
        self._stock = stock_source
        self._supplier = supplier_source
        self._draft_po_count = draft_po_count_source
        self._draft_po_sink = draft_po_sink
        self._drug_names = drug_name_source
        self._audit = audit
        self._policy = ReorderPolicy(
            window_days=window_days,
            lead_time_days=lead_time_days,
            safety_stock_days=safety_stock_days,
        )
        self._near_expiry_days = near_expiry_days

    async def run_reorder(
        self, ctx: RequestContext, *, branch_id: UUID | None = None
    ) -> ReorderRunSummary:
        """Recompute a branch's reorder suggestions from the last ``window_days`` of
        sales and current stock (PROJECT_STATE §7am). On-demand only (Q4). Clears the
        branch's prior PENDING/INSUFFICIENT_DATA rows and regenerates them; terminal
        MATERIALIZED/DISMISSED rows are left as history. Requires
        ``analytics.reorder.run``."""
        require_permission(ctx, "analytics.reorder.run")
        target = branch_id if branch_id is not None else ctx.branch_id
        date_to = date.today()
        date_from = date_to - timedelta(days=self._policy.window_days - 1)

        sold = await self._sales.sold_quantity_by_drug(
            ctx.tenant_id, target, date_from=date_from, date_to=date_to
        )
        on_hand_map = await self._stock.on_hand_by_drug(ctx.tenant_id, target)

        # Evaluate (pure), then resolve suppliers for the drugs that need reordering —
        # all before opening the write transaction, so no external call is held inside it.
        to_persist: list[ReorderSuggestion] = []
        suggested = insufficient = 0
        for d in sold:
            on_hand = on_hand_map.get(d.drug_id, Decimal("0"))
            ev = evaluate_reorder(
                quantity_sold=d.quantity_sold, on_hand=on_hand, policy=self._policy
            )
            if ev.outcome is ReorderOutcome.HEALTHY:
                continue
            if ev.outcome is ReorderOutcome.NEEDS_REORDER:
                supplier_id = await self._supplier.last_supplier_for_drug(ctx.tenant_id, d.drug_id)
                status = SuggestionStatus.PENDING
                suggested += 1
            else:  # INSUFFICIENT_DATA
                supplier_id = None
                status = SuggestionStatus.INSUFFICIENT_DATA
                insufficient += 1
            to_persist.append(
                ReorderSuggestion(
                    tenant_id=ctx.tenant_id,
                    branch_id=target,
                    drug_id=d.drug_id,
                    avg_daily_velocity=ev.avg_daily_velocity,
                    reorder_point=ev.reorder_point,
                    on_hand_at_calc=on_hand,
                    suggested_qty=ev.suggested_qty,
                    status=status,
                    supplier_id=supplier_id,
                )
            )

        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            await repo.delete_recomputable_for_branch(ctx.tenant_id, target)
            for suggestion in to_persist:
                await repo.add(suggestion)
            await uow.commit()

        await self._record(ctx, AuditAction.ANALYTICS_REORDER_RUN, "branch", target)
        return ReorderRunSummary(
            branch_id=target,
            drugs_evaluated=len(sold),
            suggested=suggested,
            insufficient_data=insufficient,
        )

    async def list_suggestions(
        self,
        ctx: RequestContext,
        *,
        branch_id: UUID | None = None,
        status: SuggestionStatus | None = None,
    ) -> list[SuggestionOutput]:
        """List a branch's reorder suggestions, optionally by status. Requires
        ``analytics.read``.

        Labels cost **two** lookups for the whole page — one for drugs, one for suppliers
        — never one per row (docs/19 khe hở G-1)."""
        require_permission(ctx, "analytics.read")
        target = branch_id if branch_id is not None else ctx.branch_id
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            items = await repo.list_by_branch(ctx.tenant_id, target, status=status)
        drug_names = await self._drug_names.names_for(ctx.tenant_id, [s.drug_id for s in items])
        supplier_names = await self._supplier.names_for(
            ctx.tenant_id, [s.supplier_id for s in items if s.supplier_id is not None]
        )
        return [
            SuggestionOutput.of(
                s,
                drug_name=drug_names.get(s.drug_id),
                supplier_name=(
                    supplier_names.get(s.supplier_id) if s.supplier_id is not None else None
                ),
            )
            for s in items
        ]

    async def materialize(self, suggestion_id: UUID, ctx: RequestContext) -> MaterializeOutput:
        """Turn a PENDING suggestion into a DRAFT purchase order via procurement
        (never auto-sent — "cảnh báo không chặn"). Requires ``analytics.reorder.run``.

        The draft PO is created in procurement's own transaction before this one
        commits; a failure here therefore leaves a harmless orphan draft (a human can
        cancel it), never a lost suggestion — the same eventual-consistency trade-off
        the cross-module event handlers accept. Raises if the suggestion is unknown,
        already actioned, or has no supplier ("chưa có NCC", Q3)."""
        require_permission(ctx, "analytics.reorder.run")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            suggestion = await repo.get(suggestion_id)
            if suggestion is None:
                raise NotFoundError(f"Không tìm thấy đề xuất {suggestion_id}")
            if not suggestion.can_materialize:
                raise ConflictError(
                    "Không thể tạo PO nháp: đề xuất không ở trạng thái chờ hoặc chưa có NCC"
                )
            assert suggestion.supplier_id is not None  # guaranteed by can_materialize
            created = await self._draft_po_sink.create_draft_po(
                ctx.tenant_id,
                suggestion.branch_id,
                actor_user_id=ctx.user_id,
                actor_permissions=ctx.permissions,
                supplier_id=suggestion.supplier_id,
                drug_id=suggestion.drug_id,
                quantity=suggestion.suggested_qty,
            )
            suggestion.mark_materialized(created.po_id)
            await repo.update(suggestion)
            await uow.commit()

        await self._record(
            ctx, AuditAction.ANALYTICS_SUGGESTION_MATERIALIZED, "reorder_suggestion", suggestion_id
        )
        return MaterializeOutput(
            suggestion_id=suggestion_id, po_id=created.po_id, po_code=created.code
        )

    async def undo_materialize(self, suggestion_id: UUID, ctx: RequestContext) -> SuggestionOutput:
        """Cancel the draft PO a materialisation created and put the suggestion back to
        PENDING — the "hoàn tác" of docs/19 §5. Requires ``analytics.reorder.run``.

        **No time window is enforced here, on purpose.** The design shows a 10-second
        undo affordance, but a server-side stopwatch would make the operation fail for
        reasons the user cannot see (a slow network makes a legitimate undo bounce) and
        would still not stop anything a determined caller wants to do. The real limit is
        a state, not a clock: the order must still be a **draft**, and procurement is the
        one that enforces that. A draft already placed with a supplier cannot be
        retracted here — and should not be, since at that point a human at the supplier
        may already be acting on it.

        ``po_id`` is read off the stored suggestion, never taken from the caller — see
        :meth:`DraftPoSink.cancel_draft_po` for why that matters.
        """
        require_permission(ctx, "analytics.reorder.run")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            suggestion = await repo.get(suggestion_id)
            if suggestion is None:
                raise NotFoundError(f"Không tìm thấy đề xuất {suggestion_id}")
            if suggestion.status is not SuggestionStatus.MATERIALIZED or suggestion.po_id is None:
                raise ConflictError("Chỉ hoàn tác được đề xuất vừa tạo đơn mua nháp")

            await self._draft_po_sink.cancel_draft_po(
                ctx.tenant_id, suggestion.branch_id, po_id=suggestion.po_id
            )
            suggestion.mark_undone()
            await repo.update(suggestion)
            await uow.commit()

        await self._record(
            ctx, AuditAction.ANALYTICS_SUGGESTION_UNDONE, "reorder_suggestion", suggestion_id
        )
        return await self._with_labels(ctx, suggestion)

    async def dismiss(self, suggestion_id: UUID, ctx: RequestContext) -> SuggestionOutput:
        """Dismiss a non-terminal suggestion. Requires ``analytics.reorder.run``.

        Labels are resolved here too, cheap as it is for one row: otherwise ``drug_name
        = None`` would mean "unresolvable" on the list endpoint and "never looked up"
        here, and one field with two meanings is how a UI ends up printing "—" for a
        drug that has a perfectly good name."""
        require_permission(ctx, "analytics.reorder.run")
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            suggestion = await repo.get(suggestion_id)
            if suggestion is None:
                raise NotFoundError(f"Không tìm thấy đề xuất {suggestion_id}")
            if suggestion.status not in (
                SuggestionStatus.PENDING,
                SuggestionStatus.INSUFFICIENT_DATA,
            ):
                raise ConflictError("Chỉ bỏ qua được đề xuất đang chờ")
            suggestion.mark_dismissed()
            await repo.update(suggestion)
            await uow.commit()

        await self._record(
            ctx, AuditAction.ANALYTICS_SUGGESTION_DISMISSED, "reorder_suggestion", suggestion_id
        )
        return await self._with_labels(ctx, suggestion)

    async def dashboard(
        self,
        ctx: RequestContext,
        *,
        date_from: date,
        date_to: date,
        branch_id: UUID | None = None,
    ) -> DashboardOutput:
        """The first-screen tiles: revenue total, top sellers, near-expiry + low-stock
        counts, draft POs awaiting approval (PROJECT_STATE §7am). Requires
        ``analytics.read``."""
        require_permission(ctx, "analytics.read")
        target = branch_id if branch_id is not None else ctx.branch_id

        sold = await self._sales.sold_quantity_by_drug(
            ctx.tenant_id, target, date_from=date_from, date_to=date_to
        )
        # Quy về 2 chữ số thập phân — cùng lý do và cùng quy ước với
        # SalesOrderListRow.subtotal: tổng của lượng(3dp)×giá(2dp) ra 5dp, một
        # hình dạng tiền không tồn tại ở cột nào. Đây là CON SỐ TO NHẤT trên bảng
        # điều hành, nên nó càng không nên là con số có hình dạng lạ.
        revenue_total = sum((d.revenue for d in sold), Decimal("0")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        top = sorted(sold, key=lambda d: d.quantity_sold, reverse=True)[:_TOP_DRUGS]
        # Names for the ten shown rows only — never for every drug sold in the period.
        names = await self._drug_names.names_for(ctx.tenant_id, [d.drug_id for d in top])
        top_drugs = [
            TopDrug(
                drug_id=d.drug_id,
                quantity_sold=d.quantity_sold,
                revenue=d.revenue,
                drug_name=names.get(d.drug_id),
            )
            for d in top
        ]
        near_expiry = await self._stock.count_near_expiry(
            ctx.tenant_id, target, within_days=self._near_expiry_days
        )
        draft_po = await self._draft_po_count.count_draft_pos(ctx.tenant_id, target)
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            low_stock = await repo.count_by_status(ctx.tenant_id, target, SuggestionStatus.PENDING)

        return DashboardOutput(
            branch_id=target,
            date_from=date_from,
            date_to=date_to,
            revenue_total=revenue_total,
            top_drugs=top_drugs,
            near_expiry_count=near_expiry,
            low_stock_count=low_stock,
            draft_po_count=draft_po,
        )

    async def _with_labels(
        self, ctx: RequestContext, suggestion: ReorderSuggestion
    ) -> SuggestionOutput:
        """Attach drug/supplier display names to a single suggestion."""
        drug_names = await self._drug_names.names_for(ctx.tenant_id, [suggestion.drug_id])
        supplier_name = None
        if suggestion.supplier_id is not None:
            supplier_names = await self._supplier.names_for(ctx.tenant_id, [suggestion.supplier_id])
            supplier_name = supplier_names.get(suggestion.supplier_id)
        return SuggestionOutput.of(
            suggestion,
            drug_name=drug_names.get(suggestion.drug_id),
            supplier_name=supplier_name,
        )

    async def _record(
        self, ctx: RequestContext, action: AuditAction, target_type: str, target_id: UUID
    ) -> None:
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                target_type=target_type,
                target_id=str(target_id),
            ).with_context(**ctx.audit_meta, branch_id=str(ctx.branch_id))
        )
