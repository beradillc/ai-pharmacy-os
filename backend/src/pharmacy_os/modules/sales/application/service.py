"""Sales use-cases: completing an (offline-originated) sale, idempotently.

The service depends only on ports; the concrete repository and unit of work are
injected as factories at composition time (see the module ``register``).

Offline-first idempotency: a sale carries a client-generated ``client_uuid``. If
a sync retries a sale already recorded, :meth:`complete_sale` returns the stored
result **without** re-processing — so no duplicate order and no duplicate
``SaleCompleted`` (which would otherwise double-dispense stock).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import TypeVar
from uuid import UUID, uuid4

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.core.errors import ConflictError, NotFoundError, ValidationError
from pharmacy_os.core.plugins import HookRegistry, PaymentCallbackError, PaymentGateway
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
    VnpayConfirmOutcome,
    VnpayInitiateOutput,
)
from pharmacy_os.modules.sales.domain import (
    Payment,
    PaymentMethod,
    SaleCompleted,
    SaleLine,
    SaleReturned,
    SalesError,
    SalesOrder,
    SaleStatus,
    SoldItem,
    ensure_allergy_acknowledged,
    ensure_prescription_valid_for_sale,
    ensure_price_override_acknowledged,
)
from pharmacy_os.modules.sales.domain.exceptions import EmptyOrderError, UnknownDrugError
from pharmacy_os.modules.sales.domain.ports import (
    AllergyRisk,
    AllergyRiskProvider,
    DrugInfo,
    DrugInfoProvider,
    DrugSalesAggRow,
    OrderRevenueRow,
    PrescriptionInfoProvider,
    SalesOrderListRow,
    SalesRepository,
)
from pharmacy_os.shared.value_objects import Money

#: Stand-in ``RequestContext`` used only to construct a repository for the one
#: tenant-unscoped read (:meth:`SalesRepository.get_across_tenants`). Its fields are
#: never read by that call path — a webhook has no real tenant/branch/user until the
#: order it names has been looked up, which is exactly what this call is for.
_LOOKUP_ONLY_CTX = RequestContext(tenant_id=UUID(int=0), branch_id=UUID(int=0), user_id=UUID(int=0))

#: ``RequestContext.user_id`` is required, but a webhook-confirmed order may have no
#: salesperson to fall back on (a VNPAY payment initiated without a signed-in cashier
#: is not a case that exists today, but the field is nullable on the order itself —
#: see ``SalesOrder.sold_by_user_id``). Never used as an audit actor: audit rows for
#: this path record ``actor_user_id=None`` explicitly, matching other no-human-actor
#: actions (see ``AuditEntry.actor_user_id``).
_SYSTEM_ACTOR = UUID(int=0)

#: How many orders a revenue-report page pulls per round-trip while bucketing —
#: same idea as the audit dashboard's export batch (PROJECT_STATE §7al): bounded
#: memory regardless of how many orders match the date range.
_REVENUE_REPORT_BATCH = 500

_T = TypeVar("_T")

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
        allergy_risk: AllergyRiskProvider | None = None,
        hook_registry: HookRegistry | None = None,
        gateway_timeout_seconds: float = 10.0,
    ) -> None:
        self._uow_factory = uow_factory
        self._repo_factory = repo_factory
        self._drug_info = drug_info
        self._prescription_info = prescription_info
        self._audit = audit
        self._allergy_risk = allergy_risk
        self._hook_registry = hook_registry
        self._gateway_timeout = gateway_timeout_seconds

    async def complete_sale(
        self,
        data: CreateSaleInput,
        ctx: RequestContext,
        *,
        require_known_drugs: bool = True,
    ) -> SaleOutput:
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
        so_dong_lech_gia = 0
        try:
            for line in data.lines:
                info = await self._drug_info_or_none(line, ctx)
                # Phương án B: đơn MỚI phải tham chiếu thuốc có thật; đường đồng bộ thì
                # không. Phân biệt `self._drug_info is None` (KHÔNG TRA ĐƯỢC — không có
                # provider, như trong test tầng service) với `info is None` (tra được,
                # danh mục nói không có mã này). Gộp hai thứ đó lại sẽ biến một cấu hình
                # thiếu thành một lỗi từ chối bán — hỏng nặng hơn nhiều thứ đang vá.
                if require_known_drugs and self._drug_info is not None and info is None:
                    raise UnknownDrugError(
                        f"Thuốc {line.drug_id} không có trong danh mục của nhà thuốc"
                    )
                requires_rx = (
                    info.requires_prescription if info is not None else line.requires_prescription
                )
                # Mã CHƯA đặt giá niêm yết (`sale_price is None`) không tính là lệch:
                # không có giá niêm yết thì không có gì để lệch, và đòi thu ngân giải
                # thích một phép so không tồn tại là vô nghĩa.
                if (
                    info is not None
                    and info.sale_price is not None
                    and line.unit_price != info.sale_price
                ):
                    so_dong_lech_gia += 1
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
            risk = await self._resolve_allergy_risk(order, ctx)
            ensure_allergy_acknowledged(risk, data.allergy_acknowledgement)
            ensure_price_override_acknowledged(so_dong_lech_gia, data.price_override_reason)
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
        if risk is not None and risk.conflict_count > 0:
            await self._record_allergy_override(ctx, order.id, risk)
        if so_dong_lech_gia > 0:
            await self._record_price_override(ctx, order.id, so_dong_lech_gia)
        return SaleOutput.of(order)

    async def accrued_by_customer(
        self,
        customer_ids: Sequence[UUID],
        ctx: RequestContext,
        *,
        created_from: datetime,
        created_to: datetime,
    ) -> dict[UUID, Decimal]:
        """Tiền từng khách đã mua trong khoảng — cơ số tích luỹ của chương trình khách quen.

        🔴 **Không** gọi `require_permission`: đây là đường cho **adapter ở composition
        root** chạy dưới danh tính hệ thống, để nhân viên chỉ cần `crm.read` là thấy được
        cột điểm trên màn Khách hàng, không phải cấp thêm `sales.read` trên toàn bộ đơn
        hàng chỉ vì một con số tổng. Cùng khuôn với đường tên thuốc cấp cho `analytics`
        (§7bt), và `ctx` do chính composition root dựng như mọi phản ứng cross-module khác.

        Vì thế nó **không được nối vào router**. Kiểm quyền là việc của use-case gọi nó.
        """
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            return await repo.accrued_by_customer(
                ctx.tenant_id, customer_ids, created_from=created_from, created_to=created_to
            )

    async def check_allergy_risk(
        self, customer_id: UUID, drug_ids: frozenset[UUID], ctx: RequestContext
    ) -> AllergyRisk | None:
        """Hỏi trước khi bán — Đ-7: quầy thấy cảnh báo ngay lúc thêm thuốc vào đơn.

        Chỉ **đọc**, không tạo đơn, không ghi gì. POS gọi mỗi lần giỏ hàng hoặc khách
        thay đổi, rồi hiện cảnh báo tại chỗ để nhân viên còn kịp đổi thuốc **trước khi
        thu tiền**.

        🔴 **Không thay thế cổng ở** :meth:`complete_sale`. Kết quả ở đây là để *hiện
        cho người xem*, không phải để cấp phép: giỏ có thể đổi sau lượt gọi này, và một
        client hoàn toàn có thể không gọi. Điểm cưỡng chế vẫn là lúc hoàn tất, quyết lại
        từ chính đơn đang được lưu. Hai chỗ hỏi cùng một cổng, khác mục đích.

        Quyền dùng ``sales.create`` chứ không phải một quyền mới: ai bán được thì phải
        thấy được cảnh báo của đơn mình đang bán. Đòi thêm quyền riêng chỉ tạo ra tình
        huống thu ngân bán được mà không thấy cảnh báo — đúng thứ Đ-6 dựng lên để tránh.

        Trả ``None`` khi chưa nối provider hoặc khách không tồn tại trong cơ sở.
        """
        require_permission(ctx, "sales.create")
        if self._allergy_risk is None:
            return None
        return await self._allergy_risk.for_sale(drug_ids, customer_id, ctx.tenant_id)

    async def _resolve_allergy_risk(
        self, order: SalesOrder, ctx: RequestContext
    ) -> AllergyRisk | None:
        """Hỏi phán quyết dị ứng cho giỏ hàng đang hoàn tất (Đ-6).

        ``None`` khi chưa nối provider (mọi cài đặt cũ giữ nguyên hành vi) hoặc khi đơn
        không ghi tên khách — bán vãng lai OTC hợp lệ không có khách, và không có khách
        thì không có dị ứng nào để đối chiếu.

        **Quyết lại ở đây, trên server, từ chính đơn đang hoàn tất** — không tin kết quả
        POS đã kiểm lúc thêm thuốc (Đ-7): giỏ có thể đổi sau lần kiểm đó, và một client
        hoàn toàn có thể bỏ qua lượt kiểm ấy. Đây là điểm cưỡng chế thật của Đ-6.
        """
        if self._allergy_risk is None or order.customer_id is None:
            return None
        return await self._allergy_risk.for_sale(
            frozenset(line.drug_id for line in order.lines), order.customer_id, ctx.tenant_id
        )

    async def _record_allergy_override(
        self, ctx: RequestContext, order_id: UUID, risk: AllergyRisk
    ) -> None:
        """Ghi vết một đơn được bán dù có cảnh báo dị ứng (Đ-6).

        Chỉ gọi sau khi ``ensure_allergy_acknowledged`` đã cho qua — tới đây nghĩa là
        người bán ĐÃ ghi lý do. Metadata thôi: số cảnh báo và mức nặng nhất, không ghi
        hoạt chất nào hay bệnh gì (giữ đúng nguyên tắc tối thiểu hoá dữ liệu mà
        ``allergy_severities_for_safety_check`` đã đặt ra).
        """
        if self._audit is None:
            return
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=AuditAction.SALES_ALLERGY_WARNING_OVERRIDDEN,
                target_type="sale",
                target_id=str(order_id),
            ).with_context(
                client_ip=ctx.client_ip,
                branch_id=str(ctx.branch_id),
                conflict_count=str(risk.conflict_count),
                worst_severity=risk.worst_severity or "",
            )
        )

    async def _record_price_override(
        self, ctx: RequestContext, order_id: UUID, so_dong: int
    ) -> None:
        """Ghi vết một đơn bán lệch giá niêm yết (Chain chốt 2026-07-31).

        Chỉ gọi sau khi ``ensure_price_override_acknowledged`` đã cho qua — tới đây nghĩa
        là người bán ĐÃ ghi lý do. Ghi **số dòng lệch**, không ghi giá từng dòng: chép giá
        vào đây là biến sổ audit thành bản sao thứ hai của ``sale_lines``, thứ nó đang canh.
        """
        if self._audit is None:
            return
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=AuditAction.SALE_PRICE_OVERRIDE,
                target_type="sale",
                target_id=str(order_id),
            ).with_context(
                client_ip=ctx.client_ip,
                branch_id=str(ctx.branch_id),
                deviation_lines=str(so_dong),
            )
        )

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

    def _resolve_payment_gateway(self) -> PaymentGateway | None:
        if self._hook_registry is None:
            return None
        return self._hook_registry.resolve(PaymentGateway)  # type: ignore[type-abstract]

    async def _with_gateway_timeout(self, awaitable: Awaitable[_T]) -> _T:
        """Chặn trần thời gian cho một lượt gọi ra cổng thanh toán (audit A-06).

        `async` làm cho timeout **khả thi**; nó không tạo ra timeout nào. Docstring của
        ``PaymentGateway`` từng nói đúng điều thứ nhất theo cách khiến người đọc tin
        điều thứ hai — trong khi **không nơi nào gọi ``asyncio.wait_for``**.

        Không có trần này, một cổng treo sẽ giữ nguyên một request cho tới khi hạ tầng
        ở đâu đó cắt nó — và thu ngân đứng nhìn màn hình bất động mà không biết vì sao.
        """
        return await asyncio.wait_for(awaitable, timeout=self._gateway_timeout)

    async def initiate_vnpay_payment(
        self, data: CreateSaleInput, ctx: RequestContext
    ) -> VnpayInitiateOutput:
        """Persist a ``DRAFT`` order and return a VNPAY payment link (Sprint 8 mục
        4/4, ``payment_vnpay``).

        Unlike :meth:`complete_sale`, this **does not** call ``order.complete()`` —
        the order stays ``DRAFT`` until the gateway's webhook confirms payment
        (:meth:`confirm_vnpay_callback`), and no :class:`SaleCompleted` is emitted
        here, so stock is not dispensed before money has actually arrived. This is
        the only place a ``DRAFT`` order is ever written to the database — every
        other sale (cash/card, :meth:`complete_sale`) is built and completed
        in-memory before it is ever persisted.

        Idempotent on ``client_uuid`` like :meth:`complete_sale`: a repeated call
        against an existing, still-``DRAFT`` order re-issues a fresh payment link
        for it rather than creating a duplicate. Once the order has moved past
        ``DRAFT`` (paid or cancelled), re-initiating is refused — the transaction
        is already settled one way or the other.
        """
        require_permission(ctx, "sales.create")
        if data.payments:
            raise ValidationError(
                "Đơn thanh toán qua cổng không nhận tiền tự khai trước — "
                "số tiền được xác nhận qua callback của cổng thanh toán"
            )
        gateway = self._resolve_payment_gateway()
        if gateway is None:
            raise ValidationError("Cổng thanh toán chưa được bật (PLUGINS__ENABLED)")

        existing = await self._order_by_client_uuid(data.client_uuid, ctx)
        if existing is not None:
            if existing.status is not SaleStatus.DRAFT:
                raise ConflictError(
                    f"Đơn {existing.id} đã ở trạng thái {existing.status.value}, "
                    "không thể khởi tạo lại thanh toán"
                )
            order = existing
        else:
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
                if not order.lines:
                    raise EmptyOrderError("Không thể khởi tạo thanh toán cho đơn rỗng")
                await self._verify_prescription_ref(order, ctx)
            except SalesError as exc:
                raise ValidationError(str(exc)) from exc

            async with self._uow_factory() as uow:
                repo = self._repo_factory(uow, ctx)
                try:
                    await repo.add(order)
                    await uow.commit()
                except Exception as exc:  # unique(tenant, client_uuid) race → treat as replay
                    await uow.rollback()
                    replay = await self._order_by_client_uuid(data.client_uuid, ctx)
                    if replay is None:
                        raise ConflictError("Không thể khởi tạo đơn") from exc
                    order = replay

        charge = await self._with_gateway_timeout(
            gateway.create_charge(
                order_id=str(order.id), amount=int(order.subtotal.amount * 100), method="vnpay"
            )
        )
        await self._record_vnpay_initiated(ctx, order.id)
        return VnpayInitiateOutput(order_id=order.id, payment_url=str(charge["payment_url"]))

    async def confirm_vnpay_callback(self, raw_payload: dict[str, str]) -> VnpayConfirmOutcome:
        """Process one VNPAY IPN callback (Sprint 8 mục 4/4).

        No :class:`RequestContext` here — the caller is VNPAY's server, not one of
        our authenticated users; the gateway's signature is the authentication.
        Verifies the signature first (never touches the order on a bad one), then
        looks the order up **across tenants** (the only call site for
        :meth:`SalesRepository.get_across_tenants` — see its docstring), then
        re-derives a proper tenant-scoped context from the order itself before any
        write. Safe to call more than once for the same transaction — VNPAY retries
        its IPN until it receives an acknowledgement, and this returns
        :attr:`VnpayConfirmOutcome.ALREADY_CONFIRMED` rather than reprocessing.
        """
        gateway = self._resolve_payment_gateway()
        if gateway is None:
            return VnpayConfirmOutcome.GATEWAY_NOT_CONFIGURED
        try:
            order_id_str = await self._with_gateway_timeout(
                gateway.verify_callback(dict(raw_payload))
            )
            order_id = UUID(order_id_str)
        except (PaymentCallbackError, ValueError):
            return VnpayConfirmOutcome.INVALID_SIGNATURE
        except TimeoutError:
            # VNPAY thử lại IPN cho tới khi nhận được xác nhận, nên hết giờ ở đây là
            # hoãn chứ không mất: lượt sau sẽ xử lý. Trả về "chưa cấu hình" thì sai —
            # cổng có đó, chỉ là không kịp trả lời.
            return VnpayConfirmOutcome.GATEWAY_TIMEOUT

        response_code = raw_payload.get("vnp_ResponseCode")
        gateway_txn_no = raw_payload.get("vnp_TransactionNo") or order_id_str

        async with self._uow_factory() as uow:
            lookup_repo = self._repo_factory(uow, _LOOKUP_ONLY_CTX)
            order = await lookup_repo.get_across_tenants(order_id)
            if order is None:
                return VnpayConfirmOutcome.ORDER_NOT_FOUND

            if order.status is not SaleStatus.DRAFT:
                already = any(p.gateway_ref == gateway_txn_no for p in order.payments)
                return (
                    VnpayConfirmOutcome.ALREADY_CONFIRMED
                    if already or order.status is SaleStatus.CANCELLED
                    else VnpayConfirmOutcome.ORDER_NOT_PENDING
                )

            ctx = RequestContext(
                tenant_id=order.tenant_id,
                branch_id=order.branch_id,
                user_id=order.sold_by_user_id or _SYSTEM_ACTOR,
                permissions=frozenset(),
            )
            repo = self._repo_factory(uow, ctx)

            if response_code != "00":
                order.cancel()
                await repo.update(order)
                await uow.commit()
                await self._record_vnpay_cancelled(ctx, order.id)
                return VnpayConfirmOutcome.CANCELLED_RECORDED

            # Never trust the gateway's amount alone — cross-check against the
            # order's own stored subtotal before treating this as paid. A
            # non-numeric value is folded into the same outcome as a wrong one
            # (int() raises ValueError on garbage) rather than a 500: the
            # signature already proves this came from the gateway, but it does
            # not prove the value parses, and both are equally "cannot proceed".
            # Left DRAFT untouched either way: this should never happen if
            # create_charge was called correctly, and cancelling would burn a
            # possibly-genuine payment sitting at the gateway — needs
            # investigation, not an automatic decision.
            expected_amount = int(order.subtotal.amount * 100)
            try:
                amount_matches = int(raw_payload["vnp_Amount"]) == expected_amount
            except (KeyError, ValueError):
                amount_matches = False
            if not amount_matches:
                return VnpayConfirmOutcome.AMOUNT_MISMATCH

            order.add_payment(
                Payment(
                    method=PaymentMethod.VNPAY,
                    amount=order.subtotal,
                    gateway_ref=gateway_txn_no,
                )
            )
            order.complete()
            try:
                await repo.update(order)
                uow.collect(
                    SaleCompleted(
                        tenant_id=order.tenant_id,
                        order_id=order.id,
                        branch_id=order.branch_id,
                        client_uuid=order.client_uuid,
                        items=tuple(
                            SoldItem(drug_id=line.drug_id, quantity=line.quantity)
                            for line in order.lines
                        ),
                    )
                )
                await uow.commit()
            except Exception:
                # unique(gateway_ref) race: a concurrent IPN for the same
                # transaction already recorded it — VNPAY's own retry behaviour,
                # not a bug. Treat as the idempotent-replay outcome.
                await uow.rollback()
                return VnpayConfirmOutcome.ALREADY_CONFIRMED

        await self._record_sale_completed(ctx, order.id)
        return VnpayConfirmOutcome.CONFIRMED

    async def _record_vnpay_initiated(self, ctx: RequestContext, order_id: UUID) -> None:
        if self._audit is None:
            return
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=AuditAction.SALE_VNPAY_INITIATED,
                target_type="sale",
                target_id=str(order_id),
            ).with_context(client_ip=ctx.client_ip, branch_id=str(ctx.branch_id))
        )

    async def _record_vnpay_cancelled(self, ctx: RequestContext, order_id: UUID) -> None:
        if self._audit is None:
            return
        await self._audit.record(
            AuditEntry(
                actor_user_id=None,  # no human actor — the gateway reported this
                tenant_id=ctx.tenant_id,
                action=AuditAction.SALE_VNPAY_CANCELLED,
                target_type="sale",
                target_id=str(order_id),
            ).with_context(branch_id=str(ctx.branch_id))
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

    async def _drug_info_or_none(self, line: SaleLineInput, ctx: RequestContext) -> DrugInfo | None:
        """Sự thật catalog cho một dòng, hoặc ``None`` khi không tra được.

        MỘT lượt tra cho cả cờ Rx lẫn giá niêm yết. Tra hai lượt sẽ mở ra khả năng hai
        câu trả lời đến từ hai trạng thái khác nhau của danh mục — hiếm, nhưng lúc đó
        đơn sẽ mang cờ Rx của giá cũ hoặc ngược lại, và không có gì báo.

        ``None`` nghĩa là *không biết*, không phải *không có*: bên gọi tự chọn cách xử.
        Với cờ Rx thì tin bên gọi (hành vi cũ, giữ nguyên); với giá thì **không coi là
        lệch** — không có giá niêm yết thì không có gì để lệch.
        """
        if self._drug_info is None:
            return None
        return await self._drug_info.get(line.drug_id, ctx.tenant_id)

    async def _resolve_requires_rx(self, line: SaleLineInput, ctx: RequestContext) -> bool:
        """Authoritative Rx status from catalog when known; else the client's flag."""
        info = await self._drug_info_or_none(line, ctx)
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
        order = await self._order_by_client_uuid(client_uuid, ctx)
        return SaleOutput.of(order) if order is not None else None

    async def _order_by_client_uuid(
        self, client_uuid: str, ctx: RequestContext
    ) -> SalesOrder | None:
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            return await repo.by_client_uuid(client_uuid)

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

    async def list_sales(
        self,
        ctx: RequestContext,
        *,
        date_from: date,
        date_to: date,
        branch_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SalesOrderListRow]:
        """Till list of orders over ``[date_from, date_to]`` (inclusive both ends),
        newest first — what the "Hoá đơn" screen shows (Sprint 10, D1).

        Requires ``sales.read``: the same grant that already lets :meth:`get_sale`
        open any single order, so listing them adds no new exposure — it only saves
        the reader from guessing ids.

        Drafts are included and carry their ``status``, unlike
        :meth:`revenue_report_rows`, which counts recognised revenue only. A shift
        handover wants to see the sale someone started and walked away from; a
        revenue figure must not. Both readings stay available because the row says
        which it is.

        ``branch_id`` narrows to one branch; omitted, the list spans every branch in
        the tenant — the same chain-level default the revenue report uses, for the
        same reason (``sales.read`` already reads across branches).
        """
        require_permission(ctx, "sales.read")
        if date_from > date_to:
            raise ValidationError("Khoảng thời gian không hợp lệ: 'từ' sau 'đến'")
        # 🔴 Cửa sổ tính theo GIỜ ĐỊA PHƯƠNG rồi mới đổi sang UTC — KHÔNG đóng dấu
        # ngày địa phương thành nửa đêm UTC.
        #
        # Bản đầu làm cách sau và đã sai thật: `created_at` lưu theo UTC, còn "hôm
        # nay" mà người bán hiểu là hôm nay theo đồng hồ treo tường. Việt Nam UTC+7,
        # nên từ 00:00 tới 07:00 sáng, ngày địa phương đã sang hôm sau mà UTC thì
        # chưa ⇒ danh sách hoá đơn **rỗng suốt buổi sáng sớm**, đúng khung giờ nhiều
        # nhà thuốc mở cửa. Bắt được lúc chạy cổng lúc 04:46 sáng, không phải bằng
        # đọc lại mã.
        #
        # `datetime.combine(...)` không kèm tzinfo ⇒ giờ địa phương của máy chủ;
        # `.astimezone(UTC)` đổi đúng mốc đó sang UTC. Với triển khai một múi giờ
        # (pilot) thì đây là câu trả lời đúng. Múi giờ theo tenant là việc khác,
        # chưa có — và khi làm thì chỗ này là nơi phải sửa.
        created_from = datetime.combine(date_from, time.min).astimezone(UTC)
        created_to = datetime.combine(date_to + timedelta(days=1), time.min).astimezone(UTC)
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            return await repo.list_orders(
                ctx.tenant_id,
                branch_id=branch_id,
                created_from=created_from,
                created_to=created_to,
                limit=limit,
                offset=offset,
            )

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

    async def aggregate_sold_by_drug(
        self,
        ctx: RequestContext,
        *,
        date_from: date,
        date_to: date,
        branch_id: UUID | None = None,
    ) -> list[DrugSalesAggRow]:
        """Net quantity + revenue sold per ``(drug_id, branch_id)`` over
        ``[date_from, date_to]`` (inclusive both ends).

        A line-level read for the ``analytics`` module — demand velocity and top
        sellers both derive from it (PROJECT_STATE §7am, Q1: velocity is measured off
        *sales*). Requires ``sales.read`` (reused, same rationale as the revenue
        report). ``branch_id`` narrows to one branch; omitted, every branch counts.

        Result is bounded by the number of distinct drugs sold, so it is returned as a
        plain list — no streaming (contrast :meth:`revenue_report_rows`)."""
        require_permission(ctx, "sales.read")
        if date_from > date_to:
            raise ValidationError("Khoảng thời gian không hợp lệ: 'từ' sau 'đến'")
        created_from = datetime.combine(date_from, time.min, tzinfo=UTC)
        created_to = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        async with self._uow_factory() as uow:
            repo = self._repo_factory(uow, ctx)
            return await repo.aggregate_sold_by_drug(
                ctx.tenant_id,
                branch_id=branch_id,
                created_from=created_from,
                created_to=created_to,
            )
