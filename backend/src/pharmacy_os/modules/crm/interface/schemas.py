"""Pydantic request/response schemas for crm."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.crm.application.dto import (
    AddAllergyInput,
    AddConditionInput,
    ConsentOutput,
    CreateCustomerInput,
    CustomerOutput,
    RecordConsentInput,
)
from pharmacy_os.modules.crm.domain import AllergySeverity, ConsentPurpose


class CreateCustomerRequest(BaseModel):
    full_name: str
    phone: str | None = None
    dob: date | None = None
    gender: str | None = None
    weight_kg: Decimal | None = Field(default=None, gt=0)
    national_id_hash: str | None = None

    def to_input(self) -> CreateCustomerInput:
        return CreateCustomerInput(
            full_name=self.full_name,
            phone=self.phone,
            dob=self.dob,
            gender=self.gender,
            weight_kg=self.weight_kg,
            national_id_hash=self.national_id_hash,
        )


class RecordConsentRequest(BaseModel):
    """Grant or revoke one purpose. ``granted`` has **no default**: Luật 91/2025
    Điều 9 forbids treating an unspoken answer as agreement, and a default here is
    exactly that."""

    purpose: ConsentPurpose
    granted: bool
    terms_version: str = Field(min_length=1, max_length=32)

    def to_input(self) -> RecordConsentInput:
        return RecordConsentInput(
            purpose=self.purpose, granted=self.granted, terms_version=self.terms_version
        )


class ConsentResponse(BaseModel):
    id: UUID
    purpose: str
    granted: bool
    terms_version: str
    recorded_at: datetime
    actor_user_id: UUID | None
    client_ip: str | None

    @classmethod
    def of(cls, out: ConsentOutput) -> ConsentResponse:
        return cls(
            id=out.id,
            purpose=out.purpose,
            granted=out.granted,
            terms_version=out.terms_version,
            recorded_at=out.recorded_at,
            actor_user_id=out.actor_user_id,
            client_ip=out.client_ip,
        )


class AddAllergyRequest(BaseModel):
    ingredient_id: UUID
    severity: AllergySeverity
    note: str | None = None

    def to_input(self) -> AddAllergyInput:
        return AddAllergyInput(
            ingredient_id=self.ingredient_id, severity=self.severity, note=self.note
        )


class AddConditionRequest(BaseModel):
    condition_code: str
    note: str | None = None

    def to_input(self) -> AddConditionInput:
        return AddConditionInput(condition_code=self.condition_code, note=self.note)


class AllergyResponse(BaseModel):
    id: UUID
    ingredient_id: UUID
    severity: str
    note: str | None


class ConditionResponse(BaseModel):
    id: UUID
    condition_code: str
    note: str | None


class MedicationHistoryResponse(BaseModel):
    id: UUID
    drug_id: UUID
    quantity: Decimal
    source: str
    ref_id: UUID
    occurred_at: datetime


class CustomerResponse(BaseModel):
    id: UUID
    full_name: str
    phone: str | None
    dob: date | None
    gender: str | None
    weight_kg: Decimal | None
    national_id_hash: str | None
    allergies: list[AllergyResponse]
    conditions: list[ConditionResponse]
    history: list[MedicationHistoryResponse]
    consents: list[ConsentResponse]
    anonymised_at: datetime | None
    health_data_allowed: bool

    @classmethod
    def of(cls, out: CustomerOutput) -> CustomerResponse:
        return cls(
            id=out.id,
            full_name=out.full_name,
            phone=out.phone,
            dob=out.dob,
            gender=out.gender,
            weight_kg=out.weight_kg,
            national_id_hash=out.national_id_hash,
            allergies=[
                AllergyResponse(
                    id=a.id, ingredient_id=a.ingredient_id, severity=a.severity, note=a.note
                )
                for a in out.allergies
            ],
            conditions=[
                ConditionResponse(id=c.id, condition_code=c.condition_code, note=c.note)
                for c in out.conditions
            ],
            history=[
                MedicationHistoryResponse(
                    id=h.id,
                    drug_id=h.drug_id,
                    quantity=h.quantity,
                    source=h.source,
                    ref_id=h.ref_id,
                    occurred_at=h.occurred_at,
                )
                for h in out.history
            ],
            consents=[ConsentResponse.of(k) for k in out.consents],
            anonymised_at=out.anonymised_at,
            health_data_allowed=out.health_data_allowed,
        )
