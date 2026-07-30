"""Sales data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from pharmacy_os.modules.sales.domain import PaymentMethod, SalesOrder


class VnpayConfirmOutcome(StrEnum):
    """What happened when a VNPAY callback was processed — gateway-agnostic on
    purpose (mirrors :class:`~pharmacy_os.core.plugins.interfaces.PaymentCallbackError`):
    the wire-format response VNPAY expects (``vnp_RspCode``/``Message``) is a
    protocol detail that belongs to the interface layer, not here."""

    CONFIRMED = "CONFIRMED"
    """First time processed: payment recorded, order completed, stock will dispense."""
    ALREADY_CONFIRMED = "ALREADY_CONFIRMED"
    """A repeat callback for a transaction already recorded — VNPAY retries until it
    gets an acknowledgement; this is the idempotent no-op path."""
    CANCELLED_RECORDED = "CANCELLED_RECORDED"
    """The gateway reported failure/cancellation; the pending order was cancelled."""
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    ORDER_NOT_PENDING = "ORDER_NOT_PENDING"
    """The order exists but is not the ``DRAFT`` this callback expects, and it does
    not match the "already confirmed, same transaction" replay case either —
    treated as suspicious rather than silently accepted."""
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    """Signature valid, but the amount VNPAY reports does not match the order's own
    stored subtotal. Should never happen if ``create_charge`` was called correctly;
    the order is left untouched (``DRAFT``) for investigation, not auto-cancelled."""
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    GATEWAY_NOT_CONFIGURED = "GATEWAY_NOT_CONFIGURED"
    GATEWAY_TIMEOUT = "GATEWAY_TIMEOUT"
    """Cổng không trả lời trong hạn (audit A-06). Khác hẳn ``GATEWAY_NOT_CONFIGURED``:
    cổng CÓ đó, chỉ là không kịp trả lời. Không mất giao dịch — VNPAY thử lại IPN cho
    tới khi nhận được xác nhận, nên đây là hoãn chứ không phải bỏ."""


class RevenueGranularity(StrEnum):
    """How the revenue report buckets orders into periods.

    Bucketing happens in Python (:mod:`sales.application.service`), not SQL
    ``date_trunc`` — that function is Postgres-only and the project's models are
    kept cross-dialect (Postgres + SQLite for tests)."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass(frozen=True, slots=True)
class RevenueRow:
    """One (period, branch, currency) bucket of the revenue report.

    ``period_start`` is the bucket's first day: the calendar day itself for
    ``DAY``, its Monday for ``WEEK``, its 1st for ``MONTH``. Split by currency too
    (not just summed) so a tenant that ever records a non-``VND`` sale never gets
    a silently-wrong mixed-currency total."""

    period_start: date
    branch_id: UUID
    currency: str
    order_count: int
    revenue_total: Decimal


@dataclass(slots=True)
class SaleLineInput:
    drug_id: UUID
    quantity: Decimal
    unit_price: Decimal
    requires_prescription: bool = False


@dataclass(slots=True)
class PaymentInput:
    method: PaymentMethod
    amount: Decimal


@dataclass(slots=True)
class CreateSaleInput:
    client_uuid: str
    lines: list[SaleLineInput] = field(default_factory=list)
    payments: list[PaymentInput] = field(default_factory=list)
    prescription_ref: UUID | None = None
    customer_id: UUID | None = None
    currency: str = "VND"
    allergy_acknowledgement: str | None = None
    """Lý do người bán vẫn bán dù có cảnh báo dị ứng (Đ-6).

    Chỉ cần khi đơn có xung đột dị ứng; mọi đơn khác để ``None``. Có mặc định nên mọi
    caller cũ không phải đổi. Chuỗi toàn khoảng trắng **không** tính là đã xác nhận —
    xem ``ensure_allergy_acknowledged``."""


@dataclass(slots=True)
class VnpayInitiateOutput:
    """What the POS/FE needs to redirect the customer to VNPAY."""

    order_id: UUID
    payment_url: str


@dataclass(slots=True)
class RegisterReturnInput:
    line_id: UUID
    quantity: Decimal


@dataclass(slots=True)
class SaleLineOutput:
    id: UUID
    drug_id: UUID
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    requires_prescription: bool
    returned_quantity: Decimal


@dataclass(slots=True)
class SaleOutput:
    id: UUID
    client_uuid: str
    status: str
    currency: str
    subtotal: Decimal
    paid_total: Decimal
    prescription_ref: UUID | None
    customer_id: UUID | None
    lines: list[SaleLineOutput]

    @classmethod
    def of(cls, order: SalesOrder) -> SaleOutput:
        return cls(
            id=order.id,
            client_uuid=order.client_uuid,
            status=order.status.value,
            currency=order.currency,
            subtotal=order.subtotal.amount,
            paid_total=order.paid_total.amount,
            prescription_ref=order.prescription_ref,
            customer_id=order.customer_id,
            lines=[
                SaleLineOutput(
                    id=line.id,
                    drug_id=line.drug_id,
                    quantity=line.quantity,
                    unit_price=line.unit_price.amount,
                    line_total=line.line_total.amount,
                    requires_prescription=line.requires_prescription,
                    returned_quantity=line.returned_quantity,
                )
                for line in order.lines
            ],
        )


@dataclass(slots=True)
class ReceiptLine:
    """One printable line: display facts resolved via ``DrugInfoProvider``.

    ``name`` falls back to the raw ``drug_id`` (as text) when catalog doesn't
    know the drug — never blank, so a receipt line is always printable.
    """

    drug_id: UUID
    name: str
    unit: str
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal


@dataclass(slots=True)
class ReceiptPayment:
    method: PaymentMethod
    amount: Decimal


@dataclass(slots=True)
class ReceiptSummaryDTO:
    """Printable projection of a completed sale — no VAT, no discount.

    Neither concept exists in the sales domain today (audited 2026-07-23 for S7
    In bill): there is no discount field anywhere on ``SalesOrder``/``SaleLine``,
    and VAT computation was explicitly descoped by the business decision behind
    this feature. ``change_amount`` is derived, not stored: the domain has no
    separate tendered/change pair, only ``Payment.amount`` per tender; any
    excess of ``paid_total`` over ``subtotal`` is treated as change due (floored
    at 0 — ``SalesOrder.complete()`` already rejects underpayment).
    """

    order_id: UUID
    tenant_id: UUID
    branch_id: UUID
    created_at: datetime
    client_uuid: str
    currency: str
    status: str
    lines: list[ReceiptLine]
    payments: list[ReceiptPayment]
    subtotal: Decimal
    paid_total: Decimal
    change_amount: Decimal
    prescription_ref: UUID | None
