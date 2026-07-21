"""Sales data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.sales.domain import PaymentMethod, SalesOrder


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
    currency: str = "VND"


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
