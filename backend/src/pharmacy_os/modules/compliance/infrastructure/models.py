"""SQLAlchemy models for compliance. Cross-dialect (Postgres + SQLite for tests)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pharmacy_os.core.db.base import Base, PkUuidMixin, TenantScopedMixin, TimestampMixin
from pharmacy_os.core.db.encrypted_types import EncryptedText


class ControlledLedgerEntryORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    """Sổ thuốc kiểm soát đặc biệt (docs/13 mục C.2.1) — hợp nhất Phụ lục VIII + XXI.

    Immutable theo domain rule — bảng này chỉ INSERT, không có cột nào được service cập nhật
    sau khi ghi (TT 20/2017 Điều 18: không hard-delete/sửa trong thời gian lưu trữ).
    """

    __tablename__ = "controlled_ledger_entries"

    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(16), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    lot_no: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_or_destination: Mapped[str] = mapped_column(String(255), nullable=False)
    document_no: Mapped[str] = mapped_column(String(64), nullable=False)
    prescription_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Tên/địa chỉ bệnh nhân mua thuốc kiểm soát đặc biệt (Phụ lục XIX) — mã hoá
    # at-rest từ Sprint 8 mục 3/4. **Đã kiểm: 2 cột này KHÔNG nằm trong CSV sổ được
    # ký** (mẫu PL VIII/XVI chỉ 8 cột + ``drug_id``), nên mã hoá chúng không thể làm
    # sai lệch ``content_sha256`` của bất kỳ chữ ký pháp lý nào đã lập.
    customer_name: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    customer_address: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class ControlledSubstanceORM(PkUuidMixin, Base):
    """Danh mục dược chất kiểm soát đặc biệt — TT 18/2026 PL I/II/III + ngưỡng PL IV/V/VI.

    Dữ liệu tham chiếu DÙNG CHUNG, không tenant-scoped (danh mục do Bộ Y tế ban hành —
    cùng lý do với ``active_ingredients`` bên catalog). Xem docs/13 mục C.1.
    """

    __tablename__ = "controlled_substances"
    __table_args__ = (
        # Tên quốc tế là khóa tra cứu khi đối chiếu công thức thuốc với danh mục.
        UniqueConstraint("name_intl", name="uq_controlled_substances_name_intl"),
    )

    name_intl: Mapped[str] = mapped_column(String(128), nullable=False)
    common_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    scientific_name: Mapped[str] = mapped_column(Text, nullable=False)
    appendix: Mapped[str] = mapped_column(String(8), nullable=False)
    limit_per_unit_mg: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    limit_concentration_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    limit_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)


class TenantComplianceConfigORM(PkUuidMixin, TimestampMixin, Base):
    """Mã cơ sở do Cục QLD cấp — 1 dòng/tenant (docs/13 mục F, entity mới)."""

    __tablename__ = "tenant_compliance_configs"
    __table_args__ = (UniqueConstraint("tenant_id", name="uq_tenant_compliance_configs_tenant"),)

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    ma_co_so_ban_le: Mapped[str] = mapped_column(String(12), nullable=False)
    ma_co_so_ban_buon: Mapped[str | None] = mapped_column(String(12), nullable=True)

    #: Thông tin cơ sở in trên hoá đơn (UAT M-02, 2026-08-01). Cùng bảng vì cùng một tờ
    #: giấy chứng nhận đủ điều kiện kinh doanh dược — tách ra hai bảng là chia đôi hồ sơ
    #: pháp lý của cơ sở, và chỗ thứ hai sẽ lệch với chỗ thứ nhất.
    #: Nullable: tenant đang chạy chưa có dữ liệu, và một cái tên nhà thuốc BỊA RA rồi in
    #: lên hoá đơn tệ hơn hẳn một ô trống. Ứng dụng rơi về ``OrgSettings`` khi trống.
    ten_co_so: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dia_chi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dien_thoai: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ma_so_thue: Mapped[str | None] = mapped_column(String(20), nullable=True)


class NationalSyncLogORM(PkUuidMixin, TimestampMixin, Base):
    """Audit truyền nhận lên CSDL Dược Quốc gia (docs/13 mục D.2).

    Tenant-scoped (chỉ ``tenant_id``, không ``branch_id`` — liên thông ở cấp cơ sở, đồng nhất
    với ``tenant_compliance_configs``). ``client_uuid`` unique theo tenant = khóa idempotency.
    Chỉ lưu ``payload_hash``, KHÔNG lưu payload thô (mục D.2).
    """

    __tablename__ = "national_sync_logs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "client_uuid", name="uq_national_sync_logs_client_uuid"),
    )

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    payload_type: Mapped[str] = mapped_column(String(16), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    client_uuid: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    request_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class NationalSyncRetryTaskORM(PkUuidMixin, TimestampMixin, Base):
    """Hàng đợi gửi lại lên CSDL Dược (docs/13 mục D.4).

    Bảng **vận hành**, không phải bảng audit: đây là chỗ duy nhất trong hệ thống giữ
    payload thô, và chỉ giữ tới khi bản ghi được cổng ACK (xóa dòng) hoặc hết lượt thử
    (``DEAD`` — còn payload để người xử lý). ``national_sync_logs`` (mục D.2) không đổi:
    vẫn chỉ ``payload_hash``.

    Không đặt FK sang ``national_sync_logs``: cùng lý do ``event_outbox`` không có FK —
    hàng đợi giao vận không được ràng vòng đời của nó vào bảng nó nhắc tới.
    """

    __tablename__ = "national_sync_retry_tasks"
    __table_args__ = (
        # 1 bản ghi cần gửi = tối đa 1 việc gửi lại; trùng khóa idempotency của log.
        UniqueConstraint(
            "tenant_id", "client_uuid", name="uq_national_sync_retry_tasks_client_uuid"
        ),
        # Truy vấn nóng của relay: "việc PENDING đã tới hạn".
        Index("ix_national_sync_retry_tasks_due", "status", "next_attempt_at"),
    )

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    sync_log_id: Mapped[UUID] = mapped_column(nullable=False)
    payload_type: Mapped[str] = mapped_column(String(16), nullable=False)
    client_uuid: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(8), nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class LedgerBookSignatureORM(PkUuidMixin, Base):
    """Xác nhận điện tử 1 sổ/1 ngày — hướng A (docs/13 mục C.5).

    Không dùng ``TenantScopedMixin`` (đã có sẵn cột ``created_at``/không cần
    ``TimestampMixin`` — ``signed_at`` chính là mốc thời gian nghiệp vụ, không cần thêm cột kỹ
    thuật trùng ý nghĩa) — khai ``tenant_id`` tay để đặt trong ``UniqueConstraint`` cùng
    ``book_type``/``book_date``, chặn ký lại ở tầng CSDL (không chỉ tầng service).
    """

    __tablename__ = "ledger_book_signatures"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "book_type", "book_date", name="uq_ledger_book_signatures_day"
        ),
    )

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    book_type: Mapped[str] = mapped_column(String(8), nullable=False)
    book_date: Mapped[date] = mapped_column(Date, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    prev_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signed_by_user_id: Mapped[UUID] = mapped_column(nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DrugReturnRecordORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    """Biên bản nhận lại thuốc GN/HT/TC (docs/13 mục C.6 — TT18 Điều 6.2 + Điều 12.1.d, PL XVIII).

    Immutable theo domain rule, cùng nguyên tắc với ``ControlledLedgerEntryORM`` — chỉ INSERT.
    """

    __tablename__ = "drug_return_records"

    # Người trả thuốc: PII mạnh nhất hệ thống (có **số CCCD**), mã hoá at-rest từ
    # Sprint 8 mục 3/4. Dùng ``EncryptedText`` chứ không phải ``EncryptedString(n)``:
    # ciphertext dài hơn bản rõ ~4/3 lần cộng nonce+tag, mà tiếng Việt có dấu chiếm
    # 3 byte/ký tự — đoán độ rộng ở đây là tự chuốc lỗi ``StringDataRightTruncation``
    # mà SQLite không tái hiện (§7ap/§7aq). Giới hạn độ dài **bản rõ** vẫn được giữ
    # nguyên ở tầng schema (``RecordDrugReturnRequest``), nên không mất kiểm tra nào.
    returner_name: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    returner_address: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    returner_id_number: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    returner_id_issuer: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    returner_id_issued_at: Mapped[date] = mapped_column(Date, nullable=False)
    returner_is_patient: Mapped[bool] = mapped_column(Boolean, nullable=False)
    receiving_pharmacist_name: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    handover_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    handover_location: Mapped[str] = mapped_column(String(500), nullable=False)

    items: Mapped[list[DrugReturnItemORM]] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DrugReturnItemORM(PkUuidMixin, Base):
    """Một dòng trong bảng danh mục thuốc nhận lại (docs/13 mục C.6, Phụ lục XVIII)."""

    __tablename__ = "drug_return_items"

    record_id: Mapped[UUID] = mapped_column(
        ForeignKey("drug_return_records.id", ondelete="CASCADE"), index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    lot_no: Mapped[str] = mapped_column(String(64), nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False)
    condition_note: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    record: Mapped[DrugReturnRecordORM] = relationship(back_populates="items")
