"""Pydantic request/response schemas for procurement."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.procurement.application.dto import (
    CreateGoodsReceiptInput,
    CreatePurchaseOrderInput,
    CreateSupplierInput,
    GoodsReceiptItemInput,
    GoodsReceiptItemOutput,
    GoodsReceiptOutput,
    PurchaseOrderItemInput,
    PurchaseOrderItemOutput,
    PurchaseOrderOutput,
    SupplierOutput,
)

# --- Supplier ---


class CreateSupplierRequest(BaseModel):
    # max_length khớp đúng độ rộng cột — không chặn thì Postgres ném
    # StringDataRightTruncationError và client nhận 500 thay vì 422 (PROJECT_STATE §7aq).
    name: str = Field(min_length=1, max_length=255)
    tax_code: str | None = Field(default=None, max_length=32)
    contact_name: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=255)
    address: str | None = None  # cột Text, không giới hạn

    def to_input(self) -> CreateSupplierInput:
        return CreateSupplierInput(
            name=self.name,
            tax_code=self.tax_code,
            contact_name=self.contact_name,
            phone=self.phone,
            email=self.email,
            address=self.address,
        )


class SupplierResponse(BaseModel):
    id: UUID
    name: str
    tax_code: str | None
    contact_name: str | None
    phone: str | None
    email: str | None
    address: str | None
    is_active: bool

    @classmethod
    def of(cls, out: SupplierOutput) -> SupplierResponse:
        return cls(
            id=out.id,
            name=out.name,
            tax_code=out.tax_code,
            contact_name=out.contact_name,
            phone=out.phone,
            email=out.email,
            address=out.address,
            is_active=out.is_active,
        )


# --- PurchaseOrder ---


class PurchaseOrderItemRequest(BaseModel):
    drug_id: UUID
    quantity_ordered: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)

    def to_input(self) -> PurchaseOrderItemInput:
        return PurchaseOrderItemInput(
            drug_id=self.drug_id,
            quantity_ordered=self.quantity_ordered,
            unit_price=self.unit_price,
        )


class CreatePurchaseOrderRequest(BaseModel):
    supplier_id: UUID
    items: list[PurchaseOrderItemRequest] = Field(default_factory=list)

    def to_input(self) -> CreatePurchaseOrderInput:
        return CreatePurchaseOrderInput(
            supplier_id=self.supplier_id, items=[it.to_input() for it in self.items]
        )


class PurchaseOrderItemResponse(BaseModel):
    id: UUID
    drug_id: UUID
    quantity_ordered: Decimal
    unit_price: Decimal
    quantity_received: Decimal

    @classmethod
    def of(cls, out: PurchaseOrderItemOutput) -> PurchaseOrderItemResponse:
        return cls(
            id=out.id,
            drug_id=out.drug_id,
            quantity_ordered=out.quantity_ordered,
            unit_price=out.unit_price,
            quantity_received=out.quantity_received,
        )


class PurchaseOrderResponse(BaseModel):
    id: UUID
    supplier_id: UUID
    status: str
    items: list[PurchaseOrderItemResponse]
    created_at: datetime
    ordered_at: datetime | None

    @classmethod
    def of(cls, out: PurchaseOrderOutput) -> PurchaseOrderResponse:
        return cls(
            id=out.id,
            supplier_id=out.supplier_id,
            status=out.status,
            items=[PurchaseOrderItemResponse.of(it) for it in out.items],
            created_at=out.created_at,
            ordered_at=out.ordered_at,
        )


# --- GoodsReceiptNote ---


class GoodsReceiptItemRequest(BaseModel):
    po_item_id: UUID
    drug_id: UUID
    quantity_received: Decimal = Field(gt=0)
    lot_no: str = Field(min_length=1, max_length=64)
    expiry_date: date
    unit_cost: Decimal = Field(ge=0)
    mfg_date: date | None = None

    def to_input(self) -> GoodsReceiptItemInput:
        return GoodsReceiptItemInput(
            po_item_id=self.po_item_id,
            drug_id=self.drug_id,
            quantity_received=self.quantity_received,
            lot_no=self.lot_no,
            expiry_date=self.expiry_date,
            unit_cost=self.unit_cost,
            mfg_date=self.mfg_date,
        )


class CreateGoodsReceiptRequest(BaseModel):
    po_id: UUID
    items: list[GoodsReceiptItemRequest] = Field(default_factory=list)

    def to_input(self) -> CreateGoodsReceiptInput:
        return CreateGoodsReceiptInput(po_id=self.po_id, items=[it.to_input() for it in self.items])


class GoodsReceiptItemResponse(BaseModel):
    id: UUID
    po_item_id: UUID
    drug_id: UUID
    quantity_received: Decimal
    lot_no: str
    expiry_date: date
    unit_cost: Decimal
    mfg_date: date | None

    @classmethod
    def of(cls, out: GoodsReceiptItemOutput) -> GoodsReceiptItemResponse:
        return cls(
            id=out.id,
            po_item_id=out.po_item_id,
            drug_id=out.drug_id,
            quantity_received=out.quantity_received,
            lot_no=out.lot_no,
            expiry_date=out.expiry_date,
            unit_cost=out.unit_cost,
            mfg_date=out.mfg_date,
        )


class GoodsReceiptResponse(BaseModel):
    id: UUID
    po_id: UUID
    status: str
    received_by: UUID
    received_at: datetime
    items: list[GoodsReceiptItemResponse]

    @classmethod
    def of(cls, out: GoodsReceiptOutput) -> GoodsReceiptResponse:
        return cls(
            id=out.id,
            po_id=out.po_id,
            status=out.status,
            received_by=out.received_by,
            received_at=out.received_at,
            items=[GoodsReceiptItemResponse.of(it) for it in out.items],
        )
