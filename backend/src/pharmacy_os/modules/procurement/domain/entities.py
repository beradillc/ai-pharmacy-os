"""Procurement aggregates: :class:`Supplier`, :class:`PurchaseOrder`, :class:`GoodsReceiptNote`.

``PurchaseOrder`` and ``GoodsReceiptNote`` are two separate aggregates linked by
``po_id`` (a plain reference, not object composition) — the same convention
``SalesOrder.prescription_ref`` uses to point at a ``Prescription`` without the
two aggregates owning each other. ``PurchaseOrder.apply_receipt`` is how a
confirmed GRN's items are folded back into the PO's received quantities; both
aggregates are saved by the application layer in the same use-case, kept
domain-pure here as plain in-memory mutation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.procurement.domain.exceptions import (
    EmptyGoodsReceiptError,
    EmptyPurchaseOrderError,
    InvalidGoodsReceiptItemError,
    InvalidGoodsReceiptStateError,
    InvalidPurchaseOrderItemError,
    InvalidPurchaseOrderStateError,
    InvalidSupplierError,
    OverReceiptError,
    UnknownPurchaseOrderItemError,
)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Supplier:
    """A goods supplier (nhà cung cấp). Not tenant-scoped here — attached at
    the repository boundary, like ``Drug``/``Customer``.
    """

    tenant_id: UUID
    name: str
    tax_code: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise InvalidSupplierError("Tên nhà cung cấp không được để trống")

    def deactivate(self) -> None:
        self.is_active = False


class PurchaseOrderStatus(StrEnum):
    DRAFT = "DRAFT"
    ORDERED = "ORDERED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    RECEIVED = "RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


@dataclass(slots=True)
class PurchaseOrderItem:
    """One ordered drug line, tracking cumulative received quantity."""

    drug_id: UUID
    quantity_ordered: Decimal
    unit_price: Decimal
    quantity_received: Decimal = Decimal("0")
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.quantity_ordered = Decimal(self.quantity_ordered)
        self.unit_price = Decimal(self.unit_price)
        self.quantity_received = Decimal(self.quantity_received)
        if self.quantity_ordered <= 0:
            raise InvalidPurchaseOrderItemError("Số lượng đặt hàng phải > 0")
        if self.unit_price < 0:
            raise InvalidPurchaseOrderItemError("Đơn giá không được âm")

    def is_fully_received(self) -> bool:
        return self.quantity_received >= self.quantity_ordered


@dataclass(slots=True)
class PurchaseOrder:
    """A purchase order to a supplier (aggregate root).

    Lifecycle: ``DRAFT`` → ``ORDERED`` → (``PARTIALLY_RECEIVED`` | ``RECEIVED``)
    → ``CLOSED``, or ``DRAFT`` → ``CANCELLED``. Items are added only while
    ``DRAFT``; receiving is applied through :meth:`apply_receipt`, called by
    the application layer once a linked :class:`GoodsReceiptNote` is confirmed.
    """

    tenant_id: UUID
    branch_id: UUID
    supplier_id: UUID
    status: PurchaseOrderStatus = PurchaseOrderStatus.DRAFT
    items: list[PurchaseOrderItem] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)
    ordered_at: datetime | None = None

    def _ensure_status(self, *allowed: PurchaseOrderStatus) -> None:
        if self.status not in allowed:
            raise InvalidPurchaseOrderStateError(
                f"Đơn mua hàng không ở trạng thái cho phép (đang {self.status}, cần {allowed})"
            )

    def add_item(self, item: PurchaseOrderItem) -> None:
        self._ensure_status(PurchaseOrderStatus.DRAFT)
        self.items.append(item)

    def place_order(self) -> None:
        """Gửi NCC: ``DRAFT`` → ``ORDERED``. Requires at least one item."""
        self._ensure_status(PurchaseOrderStatus.DRAFT)
        if not self.items:
            raise EmptyPurchaseOrderError("Không thể đặt hàng với đơn rỗng")
        self.status = PurchaseOrderStatus.ORDERED
        self.ordered_at = _now()

    def cancel(self) -> None:
        """Only allowed while still ``DRAFT`` (chưa gửi NCC)."""
        self._ensure_status(PurchaseOrderStatus.DRAFT)
        self.status = PurchaseOrderStatus.CANCELLED

    def apply_receipt(self, received_items: list[GoodsReceiptItem]) -> None:
        """Fold a confirmed GRN's items into this PO's received quantities.

        Allowed from ``ORDERED`` or ``PARTIALLY_RECEIVED`` only. Raises if a
        received line references an unknown PO item, or would push a line's
        received quantity past what was ordered.
        """
        self._ensure_status(PurchaseOrderStatus.ORDERED, PurchaseOrderStatus.PARTIALLY_RECEIVED)
        by_id = {item.id: item for item in self.items}
        for received in received_items:
            po_item = by_id.get(received.po_item_id)
            if po_item is None:
                raise UnknownPurchaseOrderItemError(
                    f"Dòng hàng {received.po_item_id} không thuộc đơn mua hàng này"
                )
            new_total = po_item.quantity_received + received.quantity_received
            if new_total > po_item.quantity_ordered:
                raise OverReceiptError(
                    f"Nhận vượt số lượng đặt hàng cho dòng {po_item.id} "
                    f"({new_total} > {po_item.quantity_ordered})"
                )
            po_item.quantity_received = new_total
        self.status = (
            PurchaseOrderStatus.RECEIVED
            if all(item.is_fully_received() for item in self.items)
            else PurchaseOrderStatus.PARTIALLY_RECEIVED
        )

    def close(self) -> None:
        """Đối chiếu xong: ``RECEIVED`` → ``CLOSED``."""
        self._ensure_status(PurchaseOrderStatus.RECEIVED)
        self.status = PurchaseOrderStatus.CLOSED


class GoodsReceiptStatus(StrEnum):
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"


@dataclass(slots=True)
class GoodsReceiptItem:
    """One received drug line — carries the lot/expiry/cost data that will
    become an ``inventory.ProductBatch`` once the cross-module step runs.
    """

    po_item_id: UUID
    drug_id: UUID
    quantity_received: Decimal
    lot_no: str
    expiry_date: date
    unit_cost: Decimal
    mfg_date: date | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.quantity_received = Decimal(self.quantity_received)
        self.unit_cost = Decimal(self.unit_cost)
        if self.quantity_received <= 0:
            raise InvalidGoodsReceiptItemError("Số lượng nhận phải > 0")
        if self.unit_cost < 0:
            raise InvalidGoodsReceiptItemError("Giá vốn không được âm")
        if not self.lot_no.strip():
            raise InvalidGoodsReceiptItemError("Số lô không được để trống")


@dataclass(slots=True)
class GoodsReceiptNote:
    """Records goods physically received against a :class:`PurchaseOrder`
    (aggregate root, kept separate from ``PurchaseOrder`` — see module note).

    Lifecycle: ``DRAFT`` → ``CONFIRMED``. Items are added only while ``DRAFT``;
    confirming requires at least one item and is final (no un-confirm) — a
    mistaken GRN is corrected by raising a new one, not mutating a confirmed
    one, since confirmation is what triggers the cross-module inventory step.
    """

    tenant_id: UUID
    branch_id: UUID
    po_id: UUID
    received_by: UUID
    status: GoodsReceiptStatus = GoodsReceiptStatus.DRAFT
    items: list[GoodsReceiptItem] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    received_at: datetime = field(default_factory=_now)

    def _ensure_status(self, *allowed: GoodsReceiptStatus) -> None:
        if self.status not in allowed:
            raise InvalidGoodsReceiptStateError(
                f"Phiếu nhập không ở trạng thái cho phép (đang {self.status}, cần {allowed})"
            )

    def add_item(self, item: GoodsReceiptItem) -> None:
        self._ensure_status(GoodsReceiptStatus.DRAFT)
        self.items.append(item)

    def confirm(self) -> None:
        """``DRAFT`` → ``CONFIRMED``. Requires at least one item."""
        self._ensure_status(GoodsReceiptStatus.DRAFT)
        if not self.items:
            raise EmptyGoodsReceiptError("Không thể xác nhận phiếu nhập rỗng")
        self.status = GoodsReceiptStatus.CONFIRMED
