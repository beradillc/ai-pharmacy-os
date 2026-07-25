"""Compliance data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.compliance.domain import (
    ControlledLedgerEntry,
    ControlledSubstanceCategory,
    DrugReturnRecord,
    LedgerBookSignature,
    LedgerBookType,
    LedgerDirection,
    NationalSyncLog,
    SyncPayloadType,
    TenantComplianceConfig,
)


@dataclass(slots=True)
class CustomerDetailInput:
    patient_name: str
    patient_address: str


@dataclass(slots=True)
class RecordControlledEntryInput:
    drug_id: UUID
    category: ControlledSubstanceCategory
    direction: LedgerDirection
    quantity: Decimal
    lot_no: str
    expiry_date: date
    transaction_at: datetime
    source_or_destination: str
    document_no: str
    prescription_code: str | None = None
    customer: CustomerDetailInput | None = None
    note: str | None = None


@dataclass(slots=True)
class CustomerDetailOutput:
    patient_name: str
    patient_address: str


@dataclass(slots=True)
class ControlledLedgerEntryOutput:
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
    customer: CustomerDetailOutput | None
    note: str | None

    @classmethod
    def of(cls, entry: ControlledLedgerEntry) -> ControlledLedgerEntryOutput:
        return cls(
            id=entry.id,
            drug_id=entry.drug_id,
            category=entry.category.value,
            direction=entry.direction.value,
            quantity=entry.quantity,
            lot_no=entry.lot_no,
            expiry_date=entry.expiry_date,
            transaction_at=entry.transaction_at,
            source_or_destination=entry.source_or_destination,
            document_no=entry.document_no,
            prescription_code=entry.prescription_code,
            customer=(
                CustomerDetailOutput(
                    patient_name=entry.customer.patient_name,
                    patient_address=entry.customer.patient_address,
                )
                if entry.customer is not None
                else None
            ),
            note=entry.note,
        )


@dataclass(slots=True)
class SetTenantComplianceConfigInput:
    ma_co_so_ban_le: str
    ma_co_so_ban_buon: str | None = None


@dataclass(slots=True)
class TenantComplianceConfigOutput:
    tenant_id: UUID
    ma_co_so_ban_le: str
    ma_co_so_ban_buon: str | None

    @classmethod
    def of(cls, config: TenantComplianceConfig) -> TenantComplianceConfigOutput:
        return cls(
            tenant_id=config.tenant_id,
            ma_co_so_ban_le=config.ma_co_so_ban_le,
            ma_co_so_ban_buon=config.ma_co_so_ban_buon,
        )


@dataclass(slots=True)
class PushSyncInput:
    """A record/batch to push to the national drug database (docs/13 mục D).

    ``payload`` is the serialized data sent to the gateway; the log stores only its hash.
    """

    payload_type: SyncPayloadType
    client_uuid: str
    payload: str


@dataclass(slots=True)
class NationalSyncLogOutput:
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
    def of(cls, log: NationalSyncLog) -> NationalSyncLogOutput:
        return cls(
            id=log.id,
            tenant_id=log.tenant_id,
            payload_type=log.payload_type.value,
            payload_hash=log.payload_hash,
            client_uuid=log.client_uuid,
            status=log.status.value,
            request_at=log.request_at,
            response_at=log.response_at,
            response_code=log.response_code,
            response_body=log.response_body,
            retry_count=log.retry_count,
            error=log.error,
        )


@dataclass(slots=True)
class LedgerBookRow:
    """Một dòng đã tính sẵn để in ra mẫu sổ Phụ lục VIII/XVI (cột (1)–(8)).

    Khác ``ControlledLedgerEntryOutput`` ở 2 chỗ do mẫu sổ quy định: số lượng tách thành
    2 cột Nhập/Xuất (một trong hai bỏ trống), và có thêm cột ``balance`` = tồn lũy kế.
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


@dataclass(slots=True)
class PeriodicReportRow:
    """Một dòng báo cáo định kỳ Mẫu số 06 (docs/13 mục C.7 — NĐ163 Điều 35.2), 1 dòng/thuốc.

    Khác hẳn ``LedgerBookRow`` (per-transaction, mẫu sổ nội bộ TT18): đây là **tổng theo kỳ 6
    tháng/năm**, mẫu gửi UBND cấp tỉnh. ``manufacturing_country``/``packaging_spec``/
    ``purchase_permit_no`` luôn ``None`` — catalog chưa lưu 3 trường này (docs/features/
    bao-cao-dinh-ky-nd163/01_DECISIONS.md mục "Nợ đã biết"), để trống có chủ đích chứ không phải
    thiếu sót, người dùng điền tay trước khi nộp. ``shrinkage`` mặc định 0 vì ledger không phân
    biệt lý do xuất (bán vs hỏng/vỡ/hết hạn) — cần kiểm kê thực tế để điền, không suy ra được.
    """

    drug_id: UUID
    drug_name: str
    dosage_form: str | None
    active_ingredients: str
    strength: str | None
    registration_no: str | None
    unit: str
    opening_balance: Decimal
    received_in_period: Decimal
    total: Decimal
    issued_in_period: Decimal
    closing_balance: Decimal
    manufacturing_country: str | None = None
    packaging_spec: str | None = None
    purchase_permit_no: str | None = None
    shrinkage: Decimal = Decimal(0)
    note: str | None = None


@dataclass(slots=True)
class ReturnedDrugItemInput:
    description: str
    unit: str
    quantity: Decimal
    lot_no: str
    expiry_date: date
    condition_note: str
    reason: str


@dataclass(slots=True)
class RecordDrugReturnInput:
    """docs/13 mục C.6 — TT18 Điều 6.2 + Điều 12.1.d, Phụ lục XVIII."""

    returner_name: str
    returner_address: str
    returner_id_number: str
    returner_id_issuer: str
    returner_id_issued_at: date
    returner_is_patient: bool
    receiving_pharmacist_name: str
    items: list[ReturnedDrugItemInput]
    handover_at: datetime
    handover_location: str


@dataclass(slots=True)
class ReturnedDrugItemOutput:
    description: str
    unit: str
    quantity: Decimal
    lot_no: str
    expiry_date: date
    condition_note: str
    reason: str


@dataclass(slots=True)
class DrugReturnRecordOutput:
    id: UUID
    returner_name: str
    returner_address: str
    returner_id_number: str
    returner_id_issuer: str
    returner_id_issued_at: date
    returner_is_patient: bool
    receiving_pharmacist_name: str
    items: list[ReturnedDrugItemOutput]
    handover_at: datetime
    handover_location: str

    @classmethod
    def of(cls, record: DrugReturnRecord) -> DrugReturnRecordOutput:
        return cls(
            id=record.id,
            returner_name=record.returner_name,
            returner_address=record.returner_address,
            returner_id_number=record.returner_id_number,
            returner_id_issuer=record.returner_id_issuer,
            returner_id_issued_at=record.returner_id_issued_at,
            returner_is_patient=record.returner_is_patient,
            receiving_pharmacist_name=record.receiving_pharmacist_name,
            items=[
                ReturnedDrugItemOutput(
                    description=i.description,
                    unit=i.unit,
                    quantity=i.quantity,
                    lot_no=i.lot_no,
                    expiry_date=i.expiry_date,
                    condition_note=i.condition_note,
                    reason=i.reason,
                )
                for i in record.items
            ],
            handover_at=record.handover_at,
            handover_location=record.handover_location,
        )


@dataclass(slots=True)
class DailyLedgerClosureExport:
    """Kết xuất cuối ngày của một mẫu sổ (docs/13 mục C.5 — ghi chú Phụ lục VIII).

    ``content`` là toàn bộ file CSV (header + mọi dòng của đúng 1 ngày), ``content_sha256`` là
    hash SHA-256 hex của ``content`` — bằng chứng toàn vẹn tại thời điểm in, dùng để phát hiện
    nếu file bị sửa sau khi in ra ký tay. Đây là điều kiện (a) của Điều 15.1 (toàn vẹn dữ liệu);
    điều kiện (d) (chữ ký số/xác nhận điện tử) là :meth:`ComplianceService.sign_daily_closure`
    (bước 6, hướng A) — 2 bước khác nhau, xem/kết xuất trước, ký sau.
    """

    book_type: str
    day: date
    content: str
    content_sha256: str
    row_count: int


@dataclass(slots=True)
class SignLedgerBookInput:
    """Ký xác nhận điện tử 1 sổ/1 ngày — hướng A (docs/13 mục C.5).

    ``current_password`` chỉ dùng tức thời để re-auth (không lưu, không log) — bắt buộc theo
    thiết kế "không chấp nhận phiên đang mở sẵn" (`01_THIET_KE_KY_DIEN_TU.md` mục 4).
    """

    book_type: LedgerBookType
    book_date: date
    current_password: str
    totp_code: str | None = None
    """Mã xác thực hai lớp, hoặc một mã dự phòng (Sprint 8).

    ``None`` khi người ký chưa bật 2FA và hệ thống chưa bắt buộc — giữ nguyên hành vi cũ,
    không phá tương thích ngược. Cũng chỉ dùng tức thời như ``current_password``: không lưu,
    không ghi log."""


@dataclass(slots=True)
class LedgerBookSignatureOutput:
    id: UUID
    book_type: str
    book_date: date
    content_sha256: str
    prev_hash: str | None
    signed_by_user_id: UUID
    signed_at: datetime

    @classmethod
    def of(cls, signature: LedgerBookSignature) -> LedgerBookSignatureOutput:
        return cls(
            id=signature.id,
            book_type=signature.book_type.value,
            book_date=signature.book_date,
            content_sha256=signature.content_sha256,
            prev_hash=signature.prev_hash,
            signed_by_user_id=signature.signed_by_user_id,
            signed_at=signature.signed_at,
        )
