"""Pydantic request/response schemas for prescription."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from pharmacy_os.modules.prescription.application.dto import (
    CreatePrescriptionInput,
    PrescriptionImageOutput,
    PrescriptionItemInput,
    PrescriptionOutput,
)
from pharmacy_os.modules.prescription.domain import PrescriptionSource


class PrescriptionItemRequest(BaseModel):
    """Một dòng thuốc trong đơn.

    ``dose``/``frequency``/``duration`` cho phép **rỗng** ở tầng trường, nhưng chỉ hợp lệ
    khi ``source=IMAGE`` — xem ``CreatePrescriptionRequest.ktra_lieu_luong``. Rỗng ở đây
    đọc là *"chưa phiên từ ảnh"*, **không** phải "không có liều".
    """

    drug_id: UUID
    quantity: Decimal = Field(gt=0)
    dose: str = Field(max_length=200)
    frequency: str = Field(max_length=200)
    duration: str = Field(max_length=200)
    instructions: str | None = None


class CreatePrescriptionRequest(BaseModel):
    customer_id: UUID
    doctor_name: str = Field(min_length=1, max_length=200)
    items: list[PrescriptionItemRequest] = Field(min_length=1)
    source: PrescriptionSource = PrescriptionSource.MANUAL
    doctor_license: str | None = Field(default=None, max_length=64)
    diagnosis: str | None = None  # cột Text, không giới hạn
    image_url: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def ktra_lieu_luong(self) -> CreatePrescriptionRequest:
        """Đơn nhập TAY vẫn phải có đủ liều · tần suất · thời gian; đơn từ ẢNH thì không.

        🔴 Vì sao nới, và nới hẹp đúng chỗ này (Chain giao 2026-07-31, GĐ chọn):

        Người đứng quầy chụp tờ đơn thì **không biết** liều/tần suất/thời gian — chúng chỉ
        có trên giấy. Bắt gõ vào là bắt chép tay lại chính tờ vừa chụp, tức làm mất lý do
        tồn tại của cái nút. Còn tự điền ``"1 viên"``/``"2 lần/ngày"`` cho qua cổng là
        **bịa dữ liệu lâm sàng** vào hồ sơ một bệnh nhân thật — cùng họ với lỗi dự án đã từ
        chối khi quyết *"hàm lượng để trống, không điền sẵn 1"*.

        Không nới rộng hơn: **``items`` vẫn phải có ít nhất một dòng**, kể cả với ảnh. Dòng
        thuốc lấy từ giỏ hàng nên mã thuốc và số lượng là **thật**. Nếu cho ``items`` rỗng,
        đơn sẽ **kẹt vĩnh viễn ở DRAFT**: ``Prescription.validate()`` ném
        ``EmptyPrescriptionError`` khi không có dòng nào, mà module này **không có đường
        thêm dòng sau khi tạo** — sẽ phải viết endpoint mới để gỡ.
        """
        if self.source is PrescriptionSource.IMAGE:
            return self
        for i, it in enumerate(self.items, start=1):
            if not (it.dose.strip() and it.frequency.strip() and it.duration.strip()):
                raise ValueError(
                    f"Dòng {i}: đơn nhập tay phải có đủ liều, tần suất và thời gian dùng"
                )
        return self

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
