"""Pydantic request/response schemas for prescription."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from pharmacy_os.modules.prescription.application.dto import (
    CreatePrescriptionInput,
    PrescriptionImageOutput,
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
    has_image: bool
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
            has_image=out.has_image,
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


class AttachPrescriptionImageRequest(BaseModel):
    """Ảnh đơn thuốc đã chụp, gửi dưới dạng base64.

    JSON base64 chứ không phải ``multipart/form-data``: máy khách là một trang web đã nén
    ảnh trong ``canvas`` và cầm sẵn chuỗi base64, còn hàng đợi offline của quầy lưu
    **JSON** — một tải trọng multipart không xếp hàng lại được khi mất mạng.

    ``max_length`` là 2,8 triệu ký tự: base64 phình ~4/3, nên đây là trần 2 MB của miền
    cộng biên. Cưỡng chế thật nằm ở ``Prescription.attach_image`` (đo byte SAU giải mã);
    giới hạn ở đây chỉ để một tải trọng khổng lồ bị chặn trước khi kịp giải mã.
    """

    image_data: str = Field(min_length=1, max_length=2_800_000)
    content_type: str = Field(max_length=32)


class PrescriptionImageResponse(BaseModel):
    prescription_id: UUID
    image_data: str
    content_type: str

    @classmethod
    def of(cls, out: PrescriptionImageOutput) -> PrescriptionImageResponse:
        return cls(
            prescription_id=out.prescription_id,
            image_data=out.image_data,
            content_type=out.content_type,
        )
