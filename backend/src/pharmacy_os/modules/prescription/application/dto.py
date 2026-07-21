"""Prescription data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.prescription.domain import Prescription, PrescriptionSource


@dataclass(slots=True)
class PrescriptionItemInput:
    drug_id: UUID
    quantity: Decimal
    dose: str
    frequency: str
    duration: str
    instructions: str | None = None


@dataclass(slots=True)
class CreatePrescriptionInput:
    customer_id: UUID
    doctor_name: str
    items: list[PrescriptionItemInput] = field(default_factory=list)
    source: PrescriptionSource = PrescriptionSource.MANUAL
    doctor_license: str | None = None
    diagnosis: str | None = None
    image_url: str | None = None


@dataclass(slots=True)
class PrescriptionItemOutput:
    id: UUID
    drug_id: UUID
    quantity: Decimal
    dose: str
    frequency: str
    duration: str
    instructions: str | None


@dataclass(slots=True)
class PrescriptionOutput:
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
    items: list[PrescriptionItemOutput]

    @classmethod
    def of(cls, rx: Prescription) -> PrescriptionOutput:
        return cls(
            id=rx.id,
            customer_id=rx.customer_id,
            doctor_name=rx.doctor_name,
            source=rx.source.value,
            doctor_license=rx.doctor_license,
            diagnosis=rx.diagnosis,
            image_url=rx.image_url,
            status=rx.status.value,
            validated_by=rx.validated_by,
            rejection_reason=rx.rejection_reason,
            items=[
                PrescriptionItemOutput(
                    id=it.id,
                    drug_id=it.drug_id,
                    quantity=it.quantity,
                    dose=it.dose,
                    frequency=it.frequency,
                    duration=it.duration,
                    instructions=it.instructions,
                )
                for it in rx.items
            ],
        )
