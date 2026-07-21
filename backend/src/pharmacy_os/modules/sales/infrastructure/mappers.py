"""Mapping between sales ORM rows and domain entities."""

from __future__ import annotations

from pharmacy_os.modules.sales.domain import (
    Payment,
    PaymentMethod,
    SaleLine,
    SalesOrder,
    SaleStatus,
)
from pharmacy_os.modules.sales.infrastructure.models import (
    PaymentORM,
    SaleLineORM,
    SalesOrderORM,
)
from pharmacy_os.shared.value_objects import Money


def to_domain(row: SalesOrderORM) -> SalesOrder:
    order = SalesOrder(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        client_uuid=row.client_uuid,
        currency=row.currency,
        prescription_ref=row.prescription_ref,
        status=SaleStatus(row.status),
    )
    order.lines = [
        SaleLine(
            id=ln.id,
            drug_id=ln.drug_id,
            quantity=ln.quantity,
            unit_price=Money(ln.unit_price, row.currency),
            requires_prescription=ln.requires_prescription,
            returned_quantity=ln.returned_quantity,
        )
        for ln in row.lines
    ]
    order.payments = [
        Payment(id=p.id, method=PaymentMethod(p.method), amount=Money(p.amount, row.currency))
        for p in row.payments
    ]
    return order


def to_orm(order: SalesOrder) -> SalesOrderORM:
    return SalesOrderORM(
        id=order.id,
        tenant_id=order.tenant_id,
        branch_id=order.branch_id,
        client_uuid=order.client_uuid,
        currency=order.currency,
        status=order.status.value,
        prescription_ref=order.prescription_ref,
        lines=[
            SaleLineORM(
                id=ln.id,
                order_id=order.id,
                drug_id=ln.drug_id,
                quantity=ln.quantity,
                unit_price=ln.unit_price.amount,
                requires_prescription=ln.requires_prescription,
                returned_quantity=ln.returned_quantity,
            )
            for ln in order.lines
        ],
        payments=[
            PaymentORM(
                id=p.id,
                order_id=order.id,
                method=p.method.value,
                amount=p.amount.amount,
            )
            for p in order.payments
        ],
    )
