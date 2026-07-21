"""Pydantic request/response schemas for sales."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.sales.application.dto import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
    SaleOutput,
)
from pharmacy_os.modules.sales.domain import PaymentMethod


class SaleLineRequest(BaseModel):
    drug_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    requires_prescription: bool = False


class PaymentRequest(BaseModel):
    method: PaymentMethod
    amount: Decimal = Field(ge=0)


class CreateSaleRequest(BaseModel):
    client_uuid: str = Field(min_length=1, max_length=64)
    lines: list[SaleLineRequest] = Field(min_length=1)
    payments: list[PaymentRequest] = Field(default_factory=list)
    prescription_ref: UUID | None = None
    currency: str = "VND"

    def to_input(self) -> CreateSaleInput:
        return CreateSaleInput(
            client_uuid=self.client_uuid,
            lines=[
                SaleLineInput(
                    drug_id=ln.drug_id,
                    quantity=ln.quantity,
                    unit_price=ln.unit_price,
                    requires_prescription=ln.requires_prescription,
                )
                for ln in self.lines
            ],
            payments=[PaymentInput(method=p.method, amount=p.amount) for p in self.payments],
            prescription_ref=self.prescription_ref,
            currency=self.currency,
        )


class SaleLineResponse(BaseModel):
    id: UUID
    drug_id: UUID
    quantity: Decimal
    unit_price: Decimal
    line_total: Decimal
    requires_prescription: bool
    returned_quantity: Decimal


class SaleResponse(BaseModel):
    id: UUID
    client_uuid: str
    status: str
    currency: str
    subtotal: Decimal
    paid_total: Decimal
    prescription_ref: UUID | None
    lines: list[SaleLineResponse]

    @classmethod
    def of(cls, out: SaleOutput) -> SaleResponse:
        return cls(
            id=out.id,
            client_uuid=out.client_uuid,
            status=out.status,
            currency=out.currency,
            subtotal=out.subtotal,
            paid_total=out.paid_total,
            prescription_ref=out.prescription_ref,
            lines=[
                SaleLineResponse(
                    id=ln.id,
                    drug_id=ln.drug_id,
                    quantity=ln.quantity,
                    unit_price=ln.unit_price,
                    line_total=ln.line_total,
                    requires_prescription=ln.requires_prescription,
                    returned_quantity=ln.returned_quantity,
                )
                for ln in out.lines
            ],
        )
