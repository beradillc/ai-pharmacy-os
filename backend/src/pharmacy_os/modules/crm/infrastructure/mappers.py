"""Mapping between crm ORM rows and domain entities."""

from __future__ import annotations

from uuid import UUID

from pharmacy_os.modules.crm.domain import (
    Allergy,
    AllergySeverity,
    Condition,
    Customer,
    MedicationHistoryEntry,
    MedicationHistorySource,
)
from pharmacy_os.modules.crm.infrastructure.models import (
    CustomerAllergyORM,
    CustomerConditionORM,
    CustomerMedicationHistoryORM,
    CustomerORM,
)


def to_domain(row: CustomerORM) -> Customer:
    customer = Customer(
        id=row.id,
        full_name=row.full_name,
        phone=row.phone,
        dob=row.dob,
        gender=row.gender,
        weight_kg=row.weight_kg,
        national_id_hash=row.national_id_hash,
    )
    customer.allergies = [
        Allergy(
            id=a.id,
            ingredient_id=a.ingredient_id,
            severity=AllergySeverity(a.severity),
            note=a.note,
        )
        for a in row.allergies
    ]
    customer.conditions = [
        Condition(id=c.id, condition_code=c.condition_code, note=c.note) for c in row.conditions
    ]
    customer.history = [
        MedicationHistoryEntry(
            id=h.id,
            drug_id=h.drug_id,
            quantity=h.quantity,
            source=MedicationHistorySource(h.source),
            ref_id=h.ref_id,
            occurred_at=h.occurred_at,
        )
        for h in row.history
    ]
    return customer


def to_orm(customer: Customer, tenant_id: UUID) -> CustomerORM:
    return CustomerORM(
        id=customer.id,
        tenant_id=tenant_id,
        full_name=customer.full_name,
        phone=customer.phone,
        dob=customer.dob,
        gender=customer.gender,
        weight_kg=customer.weight_kg,
        national_id_hash=customer.national_id_hash,
        allergies=[
            CustomerAllergyORM(
                id=a.id,
                customer_id=customer.id,
                ingredient_id=a.ingredient_id,
                severity=a.severity.value,
                note=a.note,
            )
            for a in customer.allergies
        ],
        conditions=[
            CustomerConditionORM(
                id=c.id,
                customer_id=customer.id,
                condition_code=c.condition_code,
                note=c.note,
            )
            for c in customer.conditions
        ],
        history=[
            CustomerMedicationHistoryORM(
                id=h.id,
                customer_id=customer.id,
                drug_id=h.drug_id,
                quantity=h.quantity,
                source=h.source.value,
                ref_id=h.ref_id,
                occurred_at=h.occurred_at,
            )
            for h in customer.history
        ],
    )
