"""Sales use-cases: completing an (offline-originated) sale, idempotently.

The service depends only on ports; the concrete repository and unit of work are
injected as factories at composition time (see the module ``register``).

Offline-first idempotency: a sale carries a client-generated ``client_uuid``. If
a sync retries a sale already recorded, :meth:`complete_sale` returns the stored
result **without** re-processing — so no duplicate order and no duplicate
``SaleCompleted`` (which would otherwise double-dispense stock).
"""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from uuid import UUID

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.sales.application.dto import (
    CreateSaleInput,
    ReceiptLine,
    ReceiptPayment,
    ReceiptSummaryDTO,
    SaleLineInput,
    SaleOutput,
)
from pharmacy_os.modules.sales.domain import (
    Payment,
    SaleCompleted,
    SaleLine,
    SalesError,
    SalesOrder,
    SoldItem,
    ensure_prescription_valid_for_sale,
)
from pharmacy_os.modules.sales.domain.ports import (
    DrugInfoProvider,
    PrescriptionInfoProvider,
    SalesRepository,
)
from pharmacy_os.shared.value_objects import Money

UowFactory = Callable[[], UnitOfWork]
RepoFactory = Callable[[UnitOfWork, RequestContext], SalesRepository]


class SalesService:
    def __init__(
        self,
        uow_factory: UowFactory,
        repo_factory: RepoFactory,
        drug_info: DrugInfoProvider | None = None,
        prescription_info: PrescriptionInfoProvider | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._drug_info = drug_info
        self._prescription_info = prescription_info

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

        return SaleOutput.of(order)

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
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            order = await repo.get(order_id)
        if order is None:
            raise NotFoundError(f"Không tìm thấy đơn bán {order_id}")
        return SaleOutput.of(order)

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
        change_amount = paid_total - subtotal if paid_total > subtotal else Decimal("0")
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
