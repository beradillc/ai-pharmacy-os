"""Crm data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.crm.domain import AllergySeverity, Customer


@dataclass(slots=True)
class CreateCustomerInput:
    full_name: str
    phone: str | None = None
    dob: date | None = None
    gender: str | None = None
    weight_kg: Decimal | None = None
    national_id_hash: str | None = None


@dataclass(slots=True)
class AddAllergyInput:
    ingredient_id: UUID
    severity: AllergySeverity
    note: str | None = None


@dataclass(slots=True)
class AddConditionInput:
    condition_code: str
    note: str | None = None


@dataclass(slots=True)
class AllergyOutput:
    id: UUID
    ingredient_id: UUID
    severity: str
    note: str | None


@dataclass(slots=True)
class ConditionOutput:
    id: UUID
    condition_code: str
    note: str | None


@dataclass(slots=True)
class MedicationHistoryOutput:
    id: UUID
    drug_id: UUID
    quantity: Decimal
    source: str
    ref_id: UUID
    occurred_at: datetime


@dataclass(slots=True)
class CustomerOutput:
    id: UUID
    full_name: str
    phone: str | None
    dob: date | None
    gender: str | None
    weight_kg: Decimal | None
    national_id_hash: str | None
    allergies: list[AllergyOutput]
    conditions: list[ConditionOutput]
    history: list[MedicationHistoryOutput]

    @classmethod
    def of(cls, customer: Customer) -> CustomerOutput:
        return cls(
            id=customer.id,
            full_name=customer.full_name,
            phone=customer.phone,
            dob=customer.dob,
            gender=customer.gender,
            weight_kg=customer.weight_kg,
            national_id_hash=customer.national_id_hash,
            allergies=[
                AllergyOutput(
                    id=a.id,
                    ingredient_id=a.ingredient_id,
                    severity=a.severity.value,
                    note=a.note,
                )
                for a in customer.allergies
            ],
            conditions=[
                ConditionOutput(id=c.id, condition_code=c.condition_code, note=c.note)
                for c in customer.conditions
            ],
            history=[
                MedicationHistoryOutput(
                    id=h.id,
                    drug_id=h.drug_id,
                    quantity=h.quantity,
                    source=h.source.value,
                    ref_id=h.ref_id,
                    occurred_at=h.occurred_at,
                )
                for h in customer.history
            ],
        )
