"""Mapping between prescription ORM rows and domain entities."""

from __future__ import annotations

from pharmacy_os.modules.prescription.domain import (
    Prescription,
    PrescriptionItem,
    PrescriptionSource,
    PrescriptionStatus,
)
from pharmacy_os.modules.prescription.infrastructure.models import (
    PrescriptionItemORM,
    PrescriptionORM,
)


def to_domain(row: PrescriptionORM) -> Prescription:
    rx = Prescription(
        id=row.id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        customer_id=row.customer_id,
        doctor_name=row.doctor_name,
        created_by=row.created_by,
        source=PrescriptionSource(row.source),
        doctor_license=row.doctor_license,
        diagnosis=row.diagnosis,
        image_url=row.image_url,
        image_data=row.image_data,
        image_content_type=row.image_content_type,
        status=PrescriptionStatus(row.status),
        validated_by=row.validated_by,
        rejection_reason=row.rejection_reason,
    )
    rx.items = [
        PrescriptionItem(
            id=it.id,
            drug_id=it.drug_id,
            quantity=it.quantity,
            dose=it.dose,
            frequency=it.frequency,
            duration=it.duration,
            instructions=it.instructions,
        )
        for it in row.items
    ]
    return rx


def to_orm(rx: Prescription) -> PrescriptionORM:
    return PrescriptionORM(
        id=rx.id,
        tenant_id=rx.tenant_id,
        branch_id=rx.branch_id,
        customer_id=rx.customer_id,
        doctor_name=rx.doctor_name,
        created_by=rx.created_by,
        source=rx.source.value,
        doctor_license=rx.doctor_license,
        diagnosis=rx.diagnosis,
        image_url=rx.image_url,
        image_data=rx.image_data,
        image_content_type=rx.image_content_type,
        status=rx.status.value,
        validated_by=rx.validated_by,
        rejection_reason=rx.rejection_reason,
        items=[
            PrescriptionItemORM(
                id=it.id,
                prescription_id=rx.id,
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
