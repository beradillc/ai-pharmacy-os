"""Pydantic request/response schemas for compliance, enforcing docs/13_COMPLIANCE_SPEC.md mục C.3.

Requests give an immediate 422 on malformed input independent of the domain-level rule in
``compliance.domain.rules`` (defense in depth — the domain rule remains the source of truth
for non-HTTP callers such as the cross-module composition root).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from pharmacy_os.modules.compliance.application.dto import (
    ControlledLedgerEntryOutput,
    CustomerDetailInput,
    DrugReturnRecordOutput,
    LedgerBookRow,
    LedgerBookSignatureOutput,
    NationalSyncLogOutput,
    PushSyncInput,
    RecordControlledEntryInput,
    RecordDrugReturnInput,
    ReturnedDrugItemInput,
    ReturnedDrugItemOutput,
    SetTenantComplianceConfigInput,
    SignLedgerBookInput,
    TenantComplianceConfigOutput,
)
from pharmacy_os.modules.compliance.domain import (
    ControlledSubstanceCategory,
    LedgerBookType,
    LedgerDirection,
    SyncPayloadType,
)

_PRESCRIPTION_RETAINED_CATEGORIES = (
    ControlledSubstanceCategory.GAY_NGHIEN,
    ControlledSubstanceCategory.HUONG_THAN,
)

#: Giữ đồng bộ với ``compliance.domain.rules`` — TT18 Điều 12.3 chỉ buộc 2 nhóm này lập sổ
#: xuất/nhập/tồn (Phụ lục XVI), không có nghĩa vụ Sổ theo dõi thông tin chi tiết khách hàng.
_NO_CUSTOMER_LOG_CATEGORIES = (
    ControlledSubstanceCategory.THUOC_DOC,
    ControlledSubstanceCategory.DANH_MUC_CAM,
)


class CustomerDetailRequest(BaseModel):
    """Phụ lục XXI — chỉ tên + địa chỉ, KHÔNG có trường CCCD/CMND (mẫu gốc không có cột này)."""

    patient_name: str = Field(min_length=1, max_length=255)
    patient_address: str = Field(min_length=1, max_length=500)


class RecordControlledEntryRequest(BaseModel):
    drug_id: UUID
    category: ControlledSubstanceCategory
    direction: LedgerDirection
    quantity: Decimal = Field(gt=0)
    lot_no: str = Field(min_length=1, max_length=64)
    expiry_date: date
    transaction_at: datetime
    source_or_destination: str = Field(min_length=1, max_length=255)
    document_no: str = Field(min_length=1, max_length=64)
    prescription_code: str | None = Field(default=None, max_length=64)
    customer: CustomerDetailRequest | None = None
    note: str | None = None  # cột Text, không giới hạn

    @model_validator(mode="after")
    def _enforce_controlled_sale_rule(self) -> RecordControlledEntryRequest:
        """docs/13 mục C.3 rule 2 — chỉ áp dụng chiều XUAT của thuốc kiểm soát đặc biệt."""
        if self.direction is not LedgerDirection.XUAT:
            return self
        if self.category is ControlledSubstanceCategory.NONE:
            return self
        if self.category in _NO_CUSTOMER_LOG_CATEGORIES:
            return self
        if self.customer is None:
            raise ValueError(
                "Thuốc kiểm soát đặc biệt bán ra cần thông tin khách hàng "
                "(Phụ lục XIX: tên + địa chỉ)"
            )
        if self.category in _PRESCRIPTION_RETAINED_CATEGORIES and not self.prescription_code:
            raise ValueError(
                "Thuốc gây nghiện/hướng thần bán ra cần lưu prescription_code (Điều 12.1.c)"
            )
        return self

    def to_input(self) -> RecordControlledEntryInput:
        return RecordControlledEntryInput(
            drug_id=self.drug_id,
            category=self.category,
            direction=self.direction,
            quantity=self.quantity,
            lot_no=self.lot_no,
            expiry_date=self.expiry_date,
            transaction_at=self.transaction_at,
            source_or_destination=self.source_or_destination,
            document_no=self.document_no,
            prescription_code=self.prescription_code,
            customer=(
                CustomerDetailInput(
                    patient_name=self.customer.patient_name,
                    patient_address=self.customer.patient_address,
                )
                if self.customer is not None
                else None
            ),
            note=self.note,
        )


class SetTenantComplianceConfigRequest(BaseModel):
    """Mã cơ sở do Cục QLD cấp — cỡ tối đa 12 (Bảng 1 QĐ540 mục 22/23)."""

    ma_co_so_ban_le: str = Field(min_length=1, max_length=12)
    ma_co_so_ban_buon: str | None = Field(default=None, max_length=12)

    def to_input(self) -> SetTenantComplianceConfigInput:
        return SetTenantComplianceConfigInput(
            ma_co_so_ban_le=self.ma_co_so_ban_le,
            ma_co_so_ban_buon=self.ma_co_so_ban_buon,
        )


class ReturnedDrugItemRequest(BaseModel):
    """Một dòng thuốc nhận lại (Phụ lục XVIII) — cột 'quy cách/số ĐKLH' gộp vào `description`."""

    description: str = Field(min_length=1)
    unit: str = Field(min_length=1, max_length=32)
    quantity: Decimal = Field(gt=0)
    lot_no: str = Field(min_length=1, max_length=64)
    expiry_date: date
    condition_note: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class RecordDrugReturnRequest(BaseModel):
    """docs/13 mục C.6 — TT18 Điều 6.2 + Điều 12.1.d, Phụ lục XVIII."""

    returner_name: str = Field(min_length=1, max_length=255)
    returner_address: str = Field(min_length=1, max_length=500)
    returner_id_number: str = Field(min_length=1, max_length=32)
    returner_id_issuer: str = Field(min_length=1, max_length=255)
    returner_id_issued_at: date
    returner_is_patient: bool
    receiving_pharmacist_name: str = Field(min_length=1, max_length=255)
    items: list[ReturnedDrugItemRequest] = Field(min_length=1)
    handover_at: datetime
    handover_location: str = Field(min_length=1, max_length=500)

    def to_input(self) -> RecordDrugReturnInput:
        return RecordDrugReturnInput(
            returner_name=self.returner_name,
            returner_address=self.returner_address,
            returner_id_number=self.returner_id_number,
            returner_id_issuer=self.returner_id_issuer,
            returner_id_issued_at=self.returner_id_issued_at,
            returner_is_patient=self.returner_is_patient,
            receiving_pharmacist_name=self.receiving_pharmacist_name,
            items=[
                ReturnedDrugItemInput(
                    description=i.description,
                    unit=i.unit,
                    quantity=i.quantity,
                    lot_no=i.lot_no,
                    expiry_date=i.expiry_date,
                    condition_note=i.condition_note,
                    reason=i.reason,
                )
                for i in self.items
            ],
            handover_at=self.handover_at,
            handover_location=self.handover_location,
        )


class ReturnedDrugItemResponse(BaseModel):
    description: str
    unit: str
    quantity: Decimal
    lot_no: str
    expiry_date: date
    condition_note: str
    reason: str

    @classmethod
    def of(cls, out: ReturnedDrugItemOutput) -> ReturnedDrugItemResponse:
        return cls(
            description=out.description,
            unit=out.unit,
            quantity=out.quantity,
            lot_no=out.lot_no,
            expiry_date=out.expiry_date,
            condition_note=out.condition_note,
            reason=out.reason,
        )


class DrugReturnRecordResponse(BaseModel):
    id: UUID
    returner_name: str
    returner_address: str
    returner_id_number: str
    returner_id_issuer: str
    returner_id_issued_at: date
    returner_is_patient: bool
    receiving_pharmacist_name: str
    items: list[ReturnedDrugItemResponse]
    handover_at: datetime
    handover_location: str

    @classmethod
    def of(cls, out: DrugReturnRecordOutput) -> DrugReturnRecordResponse:
        return cls(
            id=out.id,
            returner_name=out.returner_name,
            returner_address=out.returner_address,
            returner_id_number=out.returner_id_number,
            returner_id_issuer=out.returner_id_issuer,
            returner_id_issued_at=out.returner_id_issued_at,
            returner_is_patient=out.returner_is_patient,
            receiving_pharmacist_name=out.receiving_pharmacist_name,
            items=[ReturnedDrugItemResponse.of(i) for i in out.items],
            handover_at=out.handover_at,
            handover_location=out.handover_location,
        )


class CustomerDetailResponse(BaseModel):
    patient_name: str
    patient_address: str


class ControlledLedgerEntryResponse(BaseModel):
    id: UUID
    drug_id: UUID
    category: str
    direction: str
    quantity: Decimal
    lot_no: str
    expiry_date: date
    transaction_at: datetime
    source_or_destination: str
    document_no: str
    prescription_code: str | None
    customer: CustomerDetailResponse | None
    note: str | None

    @classmethod
    def of(cls, out: ControlledLedgerEntryOutput) -> ControlledLedgerEntryResponse:
        return cls(
            id=out.id,
            drug_id=out.drug_id,
            category=out.category,
            direction=out.direction,
            quantity=out.quantity,
            lot_no=out.lot_no,
            expiry_date=out.expiry_date,
            transaction_at=out.transaction_at,
            source_or_destination=out.source_or_destination,
            document_no=out.document_no,
            prescription_code=out.prescription_code,
            customer=(
                CustomerDetailResponse(
                    patient_name=out.customer.patient_name,
                    patient_address=out.customer.patient_address,
                )
                if out.customer is not None
                else None
            ),
            note=out.note,
        )


class TenantComplianceConfigResponse(BaseModel):
    tenant_id: UUID
    ma_co_so_ban_le: str
    ma_co_so_ban_buon: str | None

    @classmethod
    def of(cls, out: TenantComplianceConfigOutput) -> TenantComplianceConfigResponse:
        return cls(
            tenant_id=out.tenant_id,
            ma_co_so_ban_le=out.ma_co_so_ban_le,
            ma_co_so_ban_buon=out.ma_co_so_ban_buon,
        )


class SignLedgerBookRequest(BaseModel):
    """Ký xác nhận điện tử 1 sổ/1 ngày — hướng A (docs/13 mục C.5, bước 6/6 TT18).

    ``current_password`` bắt buộc nhập lại tại đây (re-auth) — endpoint không chấp nhận chỉ
    dựa vào ``Authorization: Bearer`` của phiên đang mở, theo đúng thiết kế
    `01_THIET_KE_KY_DIEN_TU.md` mục 4.
    """

    book_date: date
    current_password: str = Field(min_length=1)
    totp_code: str | None = Field(
        default=None,
        min_length=6,
        max_length=32,
        description="Mã xác thực hai lớp hoặc mã dự phòng; bắt buộc nếu tài khoản đã bật 2FA",
    )
    """Yếu tố thứ hai (Sprint 8). Mật khẩu một mình không đủ để ký một hành vi pháp lý
    không đảo ngược được: nếu mật khẩu lộ thì chữ ký cũng giả mạo được. Để trống khi tài
    khoản chưa bật 2FA và hệ thống chưa bắt buộc — server trả 401 nêu rõ nếu cần mã."""

    def to_input(self, book_type: LedgerBookType) -> SignLedgerBookInput:
        return SignLedgerBookInput(
            book_type=book_type,
            book_date=self.book_date,
            current_password=self.current_password,
            totp_code=self.totp_code,
        )


class LedgerBookRowResponse(BaseModel):
    """Một dòng mẫu sổ Phụ lục VIII/XVI, dạng JSON — cho **màn hình đọc trên máy**.

    Song song với ``GET …/export`` (CSV) chứ không thay nó, và hai cái phục vụ hai việc
    khác nhau: CSV là thứ **in ra ký tay** theo mẫu pháp lý, JSON là thứ dược sĩ **soát
    trước khi in**. Nếu chỉ có CSV thì màn hình phải tự phân tích lại nó — mà thứ tự cột
    CSV là một chuỗi nối hai thế giới không trình biên dịch nào canh được (kỷ luật #22),
    và một cột bị chèn thêm sẽ làm cả bảng lệch **im lặng**.

    Không mang tên thuốc: ``compliance`` không được biết lược đồ của ``catalog``. Màn hình
    tra tên qua ``GET /drugs?ids=…``, cùng khuôn màn Nhật ký tra tên nhân viên.
    """

    drug_id: UUID
    transaction_at: datetime
    source_or_destination: str
    document_no: str
    quantity_in: Decimal | None
    quantity_out: Decimal | None
    balance: Decimal
    lot_no: str
    expiry_date: date
    note: str | None

    @classmethod
    def of(cls, row: LedgerBookRow) -> LedgerBookRowResponse:
        return cls(
            drug_id=row.drug_id,
            transaction_at=row.transaction_at,
            source_or_destination=row.source_or_destination,
            document_no=row.document_no,
            quantity_in=row.quantity_in,
            quantity_out=row.quantity_out,
            balance=row.balance,
            lot_no=row.lot_no,
            expiry_date=row.expiry_date,
            note=row.note,
        )


class LedgerBookSignatureResponse(BaseModel):
    id: UUID
    book_type: str
    book_date: date
    content_sha256: str
    prev_hash: str | None
    signed_by_user_id: UUID
    signed_at: datetime

    @classmethod
    def of(cls, out: LedgerBookSignatureOutput) -> LedgerBookSignatureResponse:
        return cls(
            id=out.id,
            book_type=out.book_type,
            book_date=out.book_date,
            content_sha256=out.content_sha256,
            prev_hash=out.prev_hash,
            signed_by_user_id=out.signed_by_user_id,
            signed_at=out.signed_at,
        )


class PushSyncRequest(BaseModel):
    """Đẩy thủ công 1 bản ghi lên CSDL Dược Quốc gia.

    Luồng chính là tự động (event ``SaleCompleted`` → ``wire_compliance_sync``); endpoint này
    phục vụ việc đẩy lại thủ công khi cần (ví dụ retry sau lỗi gateway), dùng cùng
    ``client_uuid`` để idempotent với log đã có.
    """

    payload_type: SyncPayloadType
    client_uuid: str = Field(min_length=1, max_length=64)
    payload: str

    def to_input(self) -> PushSyncInput:
        return PushSyncInput(
            payload_type=self.payload_type, client_uuid=self.client_uuid, payload=self.payload
        )


class NationalSyncLogResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    payload_type: str
    payload_hash: str
    client_uuid: str
    status: str
    request_at: datetime
    response_at: datetime | None
    response_code: str | None
    response_body: str | None
    retry_count: int
    error: str | None

    @classmethod
    def of(cls, out: NationalSyncLogOutput) -> NationalSyncLogResponse:
        return cls(
            id=out.id,
            tenant_id=out.tenant_id,
            payload_type=out.payload_type,
            payload_hash=out.payload_hash,
            client_uuid=out.client_uuid,
            status=out.status,
            request_at=out.request_at,
            response_at=out.response_at,
            response_code=out.response_code,
            response_body=out.response_body,
            retry_count=out.retry_count,
            error=out.error,
        )
