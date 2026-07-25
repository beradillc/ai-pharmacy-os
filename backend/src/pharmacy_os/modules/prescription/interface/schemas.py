"""Pydantic request/response schemas for prescription."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.prescription.application.dto import (
    CreatePrescriptionInput,
    PrescriptionItemInput,
    PrescriptionOutput,
)
from pharmacy_os.modules.prescription.domain import PrescriptionSource


class PrescriptionItemRequest(BaseModel):
    drug_id: UUID
    quantity: Decimal = Field(gt=0)
    dose: str = Field(min_length=1, max_length=200)
    frequency: str = Field(min_length=1, max_length=200)
    duration: str = Field(min_length=1, max_length=200)
    instructions: str | None = None


class CreatePrescriptionRequest(BaseModel):
    customer_id: UUID
    doctor_name: str = Field(min_length=1, max_length=200)
    items: list[PrescriptionItemRequest] = Field(min_length=1)
    source: PrescriptionSource = PrescriptionSource.MANUAL
    doctor_license: str | None = Field(default=None, max_length=64)
    diagnosis: str | None = None  # cột Text, không giới hạn
    image_url: str | None = Field(default=None, max_length=500)

    def to_input(self) -> CreatePrescriptionInput:
        return CreatePrescriptionInput(
            customer_id=self.customer_id,
            doctor_name=self.doctor_name,
            items=[
                PrescriptionItemInput(
                    drug_id=it.drug_id,
                    quantity=it.quantity,
                    dose=it.dose,
                    frequency=it.frequency,
                    duration=it.duration,
                    instructions=it.instructions,
                )
                for it in self.items
            ],
            source=self.source,
            doctor_license=self.doctor_license,
            diagnosis=self.diagnosis,
            image_url=self.image_url,
        )


class RejectPrescriptionRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class PrescriptionItemResponse(BaseModel):
    id: UUID
    drug_id: UUID
    quantity: Decimal
    dose: str
    frequency: str
    duration: str
    instructions: str | None


class PrescriptionResponse(BaseModel):
    id: UUID
    customer_id: UUID
    doctor_name: str
    source: str
    doctor_license: str | None
    diagnosis: str | None
    image_url: str | None
    status: str
    validated_by: UUID | None
    rejection_reason: str | None
    items: list[PrescriptionItemResponse]

    @classmethod
    def of(cls, out: PrescriptionOutput) -> PrescriptionResponse:
        return cls(
            id=out.id,
            customer_id=out.customer_id,
            doctor_name=out.doctor_name,
            source=out.source,
            doctor_license=out.doctor_license,
            diagnosis=out.diagnosis,
            image_url=out.image_url,
            status=out.status,
            validated_by=out.validated_by,
            rejection_reason=out.rejection_reason,
            items=[
                PrescriptionItemResponse(
                    id=it.id,
                    drug_id=it.drug_id,
                    quantity=it.quantity,
                    dose=it.dose,
                    frequency=it.frequency,
                    duration=it.duration,
                    instructions=it.instructions,
                )
                for it in out.items
            ],
        )
