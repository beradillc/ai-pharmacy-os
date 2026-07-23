"""Sales aggregate: :class:`SalesOrder` with its lines, payments and returns."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.sales.domain.exceptions import (
    EmptyOrderError,
    InvalidOrderStateError,
    InvalidReturnError,
    UnderpaidError,
)
from pharmacy_os.modules.sales.domain.rules import ensure_rx_for_etc
from pharmacy_os.shared.value_objects import Money


def _now() -> datetime:
    return datetime.now(UTC)


class SaleStatus(StrEnum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"
    PARTIALLY_RETURNED = "PARTIALLY_RETURNED"
    RETURNED = "RETURNED"


class PaymentMethod(StrEnum):
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    EWALLET = "EWALLET"


@dataclass(slots=True)
class Payment:
    """A tender recorded against an order (split payments allowed)."""

    method: PaymentMethod
    amount: Money
    id: UUID = field(default_factory=uuid4)


@dataclass(slots=True)
class SaleLine:
    """One sold item. ``quantity`` is expressed in the drug's base unit.

    ``requires_prescription`` is an authoritative snapshot supplied at creation
    (from catalog, via the application layer) so the Rx rule can run without
    sales importing catalog.
    """

    drug_id: UUID
    quantity: Decimal
    unit_price: Money
    requires_prescription: bool = False
    returned_quantity: Decimal = Decimal("0")
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.quantity = Decimal(self.quantity)
        self.returned_quantity = Decimal(self.returned_quantity)
        if self.quantity <= 0:
            raise ValueError("Số lượng dòng bán phải > 0")

    @property
    def line_total(self) -> Money:
        return self.unit_price.multiply(self.quantity)

    @property
    def returnable_quantity(self) -> Decimal:
        return self.quantity - self.returned_quantity


@dataclass(slots=True)
class SalesOrder:
    """Point-of-sale order (aggregate root).

    Lifecycle: ``DRAFT`` → ``COMPLETED`` → (``PARTIALLY_RETURNED`` |
    ``RETURNED``). Lines and payments may only change while ``DRAFT``.
    """

    tenant_id: UUID
    branch_id: UUID
    client_uuid: str
    currency: str = "VND"
    prescription_ref: UUID | None = None
    customer_id: UUID | None = None
    """Optional buyer. A walk-in OTC sale legitimately has none, so this stays
    nullable forever — it is what lets a sale be linked to a CRM customer for the
    allergy check and the medication history, not a required field."""
    status: SaleStatus = SaleStatus.DRAFT
    lines: list[SaleLine] = field(default_factory=list)
    payments: list[Payment] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)

    def _ensure_draft(self) -> None:
        if self.status is not SaleStatus.DRAFT:
            raise InvalidOrderStateError(f"Đơn không ở trạng thái nháp (đang {self.status})")

    def add_line(self, line: SaleLine) -> None:
        self._ensure_draft()
        self.lines.append(line)

    def add_payment(self, payment: Payment) -> None:
        self._ensure_draft()
        if payment.amount.currency != self.currency:
            raise InvalidOrderStateError(
                f"Tiền tệ thanh toán {payment.amount.currency} khác đơn {self.currency}"
            )
        self.payments.append(payment)

    @property
    def subtotal(self) -> Money:
        total = Money.zero(self.currency)
        for line in self.lines:
            total = total.add(line.line_total)
        return total

    @property
    def paid_total(self) -> Money:
        total = Money.zero(self.currency)
        for payment in self.payments:
            total = total.add(payment.amount)
        return total

    @property
    def requires_prescription(self) -> bool:
        return any(line.requires_prescription for line in self.lines)

    def complete(self) -> None:
        """Finalise the sale: enforce Rx rule and full payment, then mark COMPLETED."""
        self._ensure_draft()
        if not self.lines:
            raise EmptyOrderError("Không thể hoàn tất đơn rỗng")
        ensure_rx_for_etc(self.requires_prescription, self.prescription_ref)
        if self.paid_total.amount < self.subtotal.amount:
            raise UnderpaidError(
                f"Chưa thanh toán đủ: cần {self.subtotal.amount}, đã trả {self.paid_total.amount}"
            )
        self.status = SaleStatus.COMPLETED

    def register_return(self, line_id: UUID, quantity: Decimal) -> None:
        """Record a (partial) return of a line and update the order status."""
        if self.status not in (SaleStatus.COMPLETED, SaleStatus.PARTIALLY_RETURNED):
            raise InvalidOrderStateError("Chỉ đơn đã hoàn tất mới được trả hàng")
        line = next((ln for ln in self.lines if ln.id == line_id), None)
        if line is None:
            raise InvalidReturnError(f"Không tìm thấy dòng {line_id} trong đơn")
        quantity = Decimal(quantity)
        if quantity <= 0 or quantity > line.returnable_quantity:
            raise InvalidReturnError(
                f"Số lượng trả không hợp lệ: {quantity} (còn trả được {line.returnable_quantity})"
            )
        line.returned_quantity += quantity
        fully = all(ln.returnable_quantity == 0 for ln in self.lines)
        self.status = SaleStatus.RETURNED if fully else SaleStatus.PARTIALLY_RETURNED
