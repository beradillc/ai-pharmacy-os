"""Pydantic request/response schemas for inventory."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.inventory.application.dto import (
    DispenseInput,
    DispenseOutput,
    NearExpiryItem,
    ReceiptOutput,
    ReceiveStockInput,
)


class ReceiveStockRequest(BaseModel):
    drug_id: UUID
    lot_no: str
    expiry_date: date
    quantity: Decimal = Field(gt=0)
    cost_price: Decimal = Field(ge=0)
    mfg_date: date | None = None

    def to_input(self) -> ReceiveStockInput:
        return ReceiveStockInput(
            drug_id=self.drug_id,
            lot_no=self.lot_no,
            expiry_date=self.expiry_date,
            quantity=self.quantity,
            cost_price=self.cost_price,
            mfg_date=self.mfg_date,
        )


class ReceiptResponse(BaseModel):
    batch_id: UUID
    drug_id: UUID
    quantity_received: Decimal
    on_hand: Decimal

    @classmethod
    def of(cls, out: ReceiptOutput) -> ReceiptResponse:
        return cls(
            batch_id=out.batch_id,
            drug_id=out.drug_id,
            quantity_received=out.quantity_received,
            on_hand=out.on_hand,
        )


class DispenseRequest(BaseModel):
    drug_id: UUID
    quantity: Decimal = Field(gt=0)
    ref_type: str | None = None
    ref_id: UUID | None = None

    def to_input(self) -> DispenseInput:
        return DispenseInput(
            drug_id=self.drug_id,
            quantity=self.quantity,
            ref_type=self.ref_type,
            ref_id=self.ref_id,
        )


class AllocationResponse(BaseModel):
    batch_id: UUID
    quantity: Decimal


class DispenseResponse(BaseModel):
    drug_id: UUID
    dispensed: Decimal
    on_hand: Decimal
    allocations: list[AllocationResponse]

    @classmethod
    def of(cls, out: DispenseOutput) -> DispenseResponse:
        return cls(
            drug_id=out.drug_id,
            dispensed=out.dispensed,
            on_hand=out.on_hand,
            allocations=[
                AllocationResponse(batch_id=a.batch_id, quantity=a.quantity)
                for a in out.allocations
            ],
        )


class OnHandResponse(BaseModel):
    drug_id: UUID
    on_hand: Decimal


class NearExpiryResponse(BaseModel):
    batch_id: UUID
    drug_id: UUID
    lot_no: str
    expiry_date: date
    quantity_received: Decimal

    @classmethod
    def of(cls, item: NearExpiryItem) -> NearExpiryResponse:
        return cls(
            batch_id=item.batch_id,
            drug_id=item.drug_id,
            lot_no=item.lot_no,
            expiry_date=item.expiry_date,
            quantity_received=item.quantity_received,
        )
