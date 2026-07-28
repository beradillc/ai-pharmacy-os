"""Procurement data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from pharmacy_os.modules.procurement.domain import GoodsReceiptNote, PurchaseOrder, Supplier


@dataclass(slots=True)
class CreateSupplierInput:
    name: str
    tax_code: str | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


@dataclass(slots=True)
class SupplierOutput:
    id: UUID
    name: str
    tax_code: str | None
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    is_active: bool

    @classmethod
    def of(cls, supplier: Supplier) -> SupplierOutput:
        return cls(
            id=supplier.id,
            name=supplier.name,
            tax_code=supplier.tax_code,
            contact_name=supplier.contact_name,
            phone=supplier.phone,
            email=supplier.email,
            address=supplier.address,
            is_active=supplier.is_active,
        )


@dataclass(slots=True)
class PurchaseOrderItemInput:
    drug_id: UUID
    quantity_ordered: Decimal
    unit_price: Decimal


@dataclass(slots=True)
class CreatePurchaseOrderInput:
    supplier_id: UUID
    items: list[PurchaseOrderItemInput] = field(default_factory=list)


@dataclass(slots=True)
class PurchaseOrderItemOutput:
    id: UUID
    drug_id: UUID
    quantity_ordered: Decimal
    unit_price: Decimal
    quantity_received: Decimal


@dataclass(slots=True)
class PurchaseOrderOutput:
    id: UUID
    code: str
    supplier_id: UUID
    status: str
    items: list[PurchaseOrderItemOutput]
    created_at: datetime
    ordered_at: datetime | None

    @classmethod
    def of(cls, po: PurchaseOrder) -> PurchaseOrderOutput:
        return cls(
            id=po.id,
            code=po.code,
            supplier_id=po.supplier_id,
            status=po.status.value,
            items=[
                PurchaseOrderItemOutput(
                    id=it.id,
                    drug_id=it.drug_id,
                    quantity_ordered=it.quantity_ordered,
                    unit_price=it.unit_price,
                    quantity_received=it.quantity_received,
                )
                for it in po.items
            ],
            created_at=po.created_at,
            ordered_at=po.ordered_at,
        )


@dataclass(slots=True)
class PurchaseOrderListItemOutput:
    """One row of the purchase-order list (Sprint 10, D2).

    Carries the **supplier name** and a **total**, which :class:`PurchaseOrderOutput`
    does not: a list is read to decide which order to open, and "NCC Dược Hậu Giang
    — 4 mặt hàng — 3.240.000 ₫" answers that where a supplier UUID and a raw item
    array do not. It drops ``items`` for the same reason ``SaleListItemResponse``
    drops ``lines``.

    ``total_amount`` is ordered quantity × unit price, i.e. what the order commits
    to — not what has been received. A draft PO created by the analytics reorder
    flow carries ``unit_price = 0`` until a human fills in the quote, so its total
    is legitimately ``0``; that is the draft saying "price not agreed yet", not a
    bug in this sum.
    """

    id: UUID
    code: str
    supplier_id: UUID
    supplier_name: str | None
    status: str
    item_count: int
    total_amount: Decimal
    created_at: datetime
    ordered_at: datetime | None

    @classmethod
    def of(cls, po: PurchaseOrder, supplier_name: str | None) -> PurchaseOrderListItemOutput:
        return cls(
            id=po.id,
            code=po.code,
            supplier_id=po.supplier_id,
            supplier_name=supplier_name,
            status=po.status.value,
            item_count=len(po.items),
            # Lượng là Numeric(18,3), giá là Numeric(18,2) ⇒ tích ra 5 chữ số thập
            # phân ("220000.00000"). Quy về 2 chữ số — đúng độ rộng mọi cột tiền
            # trong hệ thống — để API không phát ra một con số tiền có hình dạng
            # không tồn tại ở đâu khác. Làm tròn nửa lên, quyết định tại đây chứ
            # không để mỗi client tự làm tròn một kiểu.
            total_amount=sum(
                (it.quantity_ordered * it.unit_price for it in po.items), Decimal("0")
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            created_at=po.created_at,
            ordered_at=po.ordered_at,
        )


@dataclass(slots=True)
class GoodsReceiptItemInput:
    po_item_id: UUID
    drug_id: UUID
    quantity_received: Decimal
    lot_no: str
    expiry_date: date
    unit_cost: Decimal
    mfg_date: date | None = None


@dataclass(slots=True)
class CreateGoodsReceiptInput:
    po_id: UUID
    items: list[GoodsReceiptItemInput] = field(default_factory=list)


@dataclass(slots=True)
class GoodsReceiptItemOutput:
    id: UUID
    po_item_id: UUID
    drug_id: UUID
    quantity_received: Decimal
    lot_no: str
    expiry_date: date
    unit_cost: Decimal
    mfg_date: date | None


@dataclass(slots=True)
class GoodsReceiptOutput:
    id: UUID
    po_id: UUID
    status: str
    received_by: UUID
    received_at: datetime
    items: list[GoodsReceiptItemOutput]

    @classmethod
    def of(cls, grn: GoodsReceiptNote) -> GoodsReceiptOutput:
        return cls(
            id=grn.id,
            po_id=grn.po_id,
            status=grn.status.value,
            received_by=grn.received_by,
            received_at=grn.received_at,
            items=[
                GoodsReceiptItemOutput(
                    id=it.id,
                    po_item_id=it.po_item_id,
                    drug_id=it.drug_id,
                    quantity_received=it.quantity_received,
                    lot_no=it.lot_no,
                    expiry_date=it.expiry_date,
                    unit_cost=it.unit_cost,
                    mfg_date=it.mfg_date,
                )
                for it in grn.items
            ],
        )
