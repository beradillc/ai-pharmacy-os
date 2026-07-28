"""Procurement data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
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
