"""Compliance entities: national drug record and controlled-substance ledger.

See docs/13_COMPLIANCE_SPEC.md for the legal traceability of every field below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.compliance.domain.exceptions import (
    InvalidSyncStateError,
    NotControlledSubstanceError,
)


def _now() -> datetime:
    return datetime.now(UTC)


class ControlledSubstanceCategory(StrEnum):
    """Phân loại thuốc kiểm soát đặc biệt (TT 18/2026 Phụ lục VII). Xem docs/13 mục C.1.

    Phạm vi module là cơ sở bán lẻ. ``THUOC_DOC``/``DANH_MUC_CAM`` được bổ sung 2026-07-25:
    TT18 Điều 12.3 buộc **chính cơ sở bán lẻ** lập sổ xuất/nhập/tồn (Phụ lục XVI) cho 2 nhóm
    này — TT20/2017 không có nghĩa vụ đó nên bản cũ đã loại chúng khỏi enum, tiền đề đó sai.
    Thuốc phóng xạ vẫn ngoài phạm vi (nhà thuốc bán lẻ không kinh doanh).
    """

    GAY_NGHIEN = "GAY_NGHIEN"  # gây nghiện
    HUONG_THAN = "HUONG_THAN"  # hướng thần
    TIEN_CHAT = "TIEN_CHAT"  # tiền chất dùng làm thuốc
    PHOI_HOP_GN = "PHOI_HOP_GN"  # dạng phối hợp chứa gây nghiện
    PHOI_HOP_HT = "PHOI_HOP_HT"  # dạng phối hợp chứa hướng thần
    PHOI_HOP_TC = "PHOI_HOP_TC"  # dạng phối hợp chứa tiền chất
    THUOC_DOC = "THUOC_DOC"  # thuốc độc, nguyên liệu độc làm thuốc (Điều 12.3)
    DANH_MUC_CAM = "DANH_MUC_CAM"  # thuốc/dược chất thuộc danh mục chất bị cấm (Điều 12.3)
    NONE = "NONE"  # không thuộc diện kiểm soát — mặc định


class LedgerBookType(StrEnum):
    """Mẫu sổ xuất/nhập/tồn phải dùng cho một nhóm thuốc (docs/13 mục C.2.1).

    Hai mẫu sổ khác nhau, không gộp được: Phụ lục XVI có thêm cột đầu sổ ``nhà sản xuất``
    và áp cho nhóm thuốc khác Phụ lục VIII.
    """

    PL_VIII = "PL_VIII"  # GN/HT/TC + nguyên liệu (Điều 12.1.a)
    PL_XVI = "PL_XVI"  # dạng phối hợp + thuốc độc + danh mục cấm (Điều 12.3)


_PL_XVI_CATEGORIES = frozenset(
    {
        ControlledSubstanceCategory.PHOI_HOP_GN,
        ControlledSubstanceCategory.PHOI_HOP_HT,
        ControlledSubstanceCategory.PHOI_HOP_TC,
        ControlledSubstanceCategory.THUOC_DOC,
        ControlledSubstanceCategory.DANH_MUC_CAM,
    }
)


def book_type_for(category: ControlledSubstanceCategory) -> LedgerBookType:
    """Mẫu sổ tương ứng với nhóm thuốc — suy ra, KHÔNG lưu trùng xuống CSDL.

    Lưu thành cột riêng thì có 2 nguồn sự thật cho cùng một dữ kiện và chúng lệch nhau được;
    ``category`` đã đủ để suy ra nên chỉ suy ra tại chỗ.
    """
    if category is ControlledSubstanceCategory.NONE:
        raise NotControlledSubstanceError("Thuốc không thuộc diện kiểm soát thì không có sổ")
    return LedgerBookType.PL_XVI if category in _PL_XVI_CATEGORIES else LedgerBookType.PL_VIII


class LedgerDirection(StrEnum):
    """Chiều giao dịch trong Sổ theo dõi xuất/nhập/tồn (Phụ lục VIII, TT 20/2017)."""

    NHAP = "NHAP"
    XUAT = "XUAT"


class ControlledSubstanceAppendix(StrEnum):
    """Phụ lục danh mục dược chất của TT 18/2026 (docs/13 mục C.1).

    Chỉ 3 danh mục hoạt chất — không gồm các phụ lục biểu mẫu sổ sách.
    """

    PL_I = "PL_I"  # Danh mục dược chất gây nghiện (42 chất)
    PL_II = "PL_II"  # Danh mục dược chất hướng thần (72 chất)
    PL_III = "PL_III"  # Danh mục tiền chất dùng làm thuốc (8 chất)


_APPENDIX_CATEGORY: dict[ControlledSubstanceAppendix, ControlledSubstanceCategory] = {
    ControlledSubstanceAppendix.PL_I: ControlledSubstanceCategory.GAY_NGHIEN,
    ControlledSubstanceAppendix.PL_II: ControlledSubstanceCategory.HUONG_THAN,
    ControlledSubstanceAppendix.PL_III: ControlledSubstanceCategory.TIEN_CHAT,
}


@dataclass(frozen=True, slots=True)
class ControlledSubstance:
    """Một dược chất trong danh mục kiểm soát đặc biệt — dữ liệu tham chiếu DÙNG CHUNG.

    Nguồn: TT 18/2026 Phụ lục I/II/III (danh mục) + Phụ lục IV/V/VI (giới hạn nồng độ,
    hàm lượng trong thuốc dạng phối hợp). Xem docs/13 mục C.1.

    Không tenant-scoped: danh mục do Bộ Y tế ban hành, mọi cơ sở dùng chung.

    ``limit_per_unit_mg`` / ``limit_concentration_pct`` là **ngưỡng phân loại** theo Phụ lục VII:
    hàm lượng/nồng độ **không vượt** ngưỡng ⇒ thuốc dạng phối hợp; **vượt** ngưỡng ⇒ thuốc
    GN/HT/TC nguyên nhóm. ``None`` = phụ lục giới hạn không quy định ngưỡng cho chất này.
    """

    name_intl: str
    scientific_name: str
    appendix: ControlledSubstanceAppendix
    common_name: str | None = None
    limit_per_unit_mg: Decimal | None = None
    limit_concentration_pct: Decimal | None = None
    limit_note: str | None = None
    effective_from: date | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.name_intl.strip():
            raise ValueError("Tên quốc tế của dược chất không được để trống")
        for attr in ("limit_per_unit_mg", "limit_concentration_pct"):
            value = getattr(self, attr)
            if value is not None:
                object.__setattr__(self, attr, Decimal(value))
                if getattr(self, attr) <= 0:
                    raise ValueError(f"{attr} phải > 0 nếu có quy định")

    @property
    def category(self) -> ControlledSubstanceCategory:
        """Nhóm kiểm soát suy ra từ phụ lục — PL I ⇒ GN, PL II ⇒ HT, PL III ⇒ TC."""
        return _APPENDIX_CATEGORY[self.appendix]

    def is_effective_on(self, day: date) -> bool:
        """Chất đã có hiệu lực quản lý tại ngày ``day`` chưa.

        Dùng cho các chất được đưa vào danh mục theo mốc riêng — TT18 Điều 16.2:
        Etomidate và Carisoprodol là dược chất hướng thần **từ 01/6/2026**, sớm hơn
        ngày hiệu lực chung của Thông tư (16/7/2026).
        """
        return self.effective_from is None or day >= self.effective_from


@dataclass(frozen=True, slots=True)
class NationalDrugRecord:
    """23 trường chuẩn đầu ra Bảng 1 QĐ540 (docs/13 mục B).

    Value object — không có bảng riêng trong CSDL nội bộ (xem migration `0005_compliance`).
    Lắp ráp tại thời điểm đồng bộ từ catalog/inventory/sales qua read-port; các trường ngày/mã
    được mã hóa bằng converter helpers (mục A) chỉ khi xuất payload lên CSDL Dược Quốc gia.
    """

    ma_thuoc: str
    ten_thuoc: str
    so_dang_ky: str
    ten_hoat_chat: str
    nong_do_ham_luong: str
    nha_san_xuat: str
    nuoc_san_xuat: str
    nha_nhap_khau: str
    quy_cach_dong_goi: str
    dang_bao_che: str
    don_vi_dong_goi_nn: str
    gia_ban_le: Decimal
    so_lo: str
    han_dung: date
    so_luong_nhap: Decimal
    so_luong_ban: Decimal
    so_luong_ton: Decimal
    don_vi_bthuoc_cho_csbl: str
    so_hoa_don_mthuoc: str
    ngay_nhap: datetime
    ngay_ban: datetime
    ma_co_so_ban_le: str
    ma_co_so_ban_buon: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "gia_ban_le", Decimal(self.gia_ban_le))
        object.__setattr__(self, "so_luong_nhap", Decimal(self.so_luong_nhap))
        object.__setattr__(self, "so_luong_ban", Decimal(self.so_luong_ban))
        object.__setattr__(self, "so_luong_ton", Decimal(self.so_luong_ton))


@dataclass(frozen=True, slots=True)
class CustomerDetail:
    """Thông tin khách hàng theo mẫu Sổ Phụ lục XXI (TT 20/2017).

    Chỉ ``patient_name`` + ``patient_address`` — mẫu sổ gốc (đã đối chiếu cột) KHÔNG có cột
    số CCCD/CMND, nên KHÔNG thêm ``patient_id`` (docs/13 mục C.3 rule 2).
    """

    patient_name: str
    patient_address: str

    def __post_init__(self) -> None:
        if not self.patient_name.strip():
            raise ValueError("Tên khách hàng không được để trống (Phụ lục XXI)")
        if not self.patient_address.strip():
            raise ValueError("Địa chỉ khách hàng không được để trống (Phụ lục XXI)")


@dataclass(slots=True)
class ControlledLedgerEntry:
    """Một dòng Sổ thuốc kiểm soát đặc biệt (docs/13 mục C.2.1).

    Hợp nhất cột của 2 mẫu sổ bắt buộc: Phụ lục VIII (xuất/nhập/tồn — mọi giao dịch) và
    Phụ lục XXI (thông tin khách hàng — chỉ áp dụng chiều ``XUAT``). Immutable sau khi tạo:
    không có phương thức sửa/xóa (TT 20/2017 Điều 18 — không hard-delete trong thời gian lưu trữ).
    """

    tenant_id: UUID
    branch_id: UUID
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
    customer: CustomerDetail | None = None
    note: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        self.quantity = Decimal(self.quantity)
        if self.category is ControlledSubstanceCategory.NONE:
            raise NotControlledSubstanceError(
                "ControlledLedgerEntry chỉ ghi cho thuốc thuộc diện kiểm soát đặc biệt"
            )
        if self.quantity <= 0:
            raise ValueError("Số lượng giao dịch phải > 0")


@dataclass(slots=True)
class TenantComplianceConfig:
    """Mã cơ sở do Cục QLD cấp (docs/13 mục B field 22/23, mục F).

    GAP xác nhận khi khóa spec: KHÔNG có bảng cấu hình tenant nào tồn tại trước đó — đây là
    entity mới, không phải bổ sung field vào bảng có sẵn.
    """

    tenant_id: UUID
    ma_co_so_ban_le: str
    ma_co_so_ban_buon: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if not self.ma_co_so_ban_le.strip():
            raise ValueError("ma_co_so_ban_le không được để trống")


class SyncPayloadType(StrEnum):
    """Loại bản ghi đẩy lên CSDL Dược (docs/13 mục D.2 — payload_type drug/sale/prescription)."""

    DRUG = "drug"
    SALE = "sale"
    PRESCRIPTION = "prescription"


class SyncStatus(StrEnum):
    """Trạng thái truyền nhận 1 bản ghi lên CSDL Dược (docs/13 mục D.2)."""

    PENDING = "PENDING"  # đã tạo, chưa gửi
    SENT = "SENT"  # đã gửi, chờ phản hồi
    ACK = "ACK"  # cổng CSDL Dược đã xác nhận nhận
    FAILED = "FAILED"  # gửi lỗi / bị từ chối


@dataclass(slots=True)
class NationalSyncLog:
    """Audit truyền nhận 1 bản ghi/lô lên CSDL Dược Quốc gia (docs/13 mục D.2).

    Chỉ lưu ``payload_hash`` (không lưu payload thô — mục D.2 chỉ liệt kê hash). ``client_uuid``
    dùng làm khóa idempotency (unique theo tenant). Vòng đời:
    ``PENDING`` → ``SENT`` → ``ACK`` hoặc ``FAILED``; ``FAILED`` có thể gửi lại (``mark_sent``).
    Tenant-scoped (chỉ ``tenant_id``, không ``branch_id`` — liên thông ở cấp cơ sở, đồng nhất với
    :class:`TenantComplianceConfig`).
    """

    tenant_id: UUID
    payload_type: SyncPayloadType
    payload_hash: str
    client_uuid: str
    status: SyncStatus = SyncStatus.PENDING
    request_at: datetime = field(default_factory=_now)
    response_at: datetime | None = None
    response_code: str | None = None
    response_body: str | None = None
    retry_count: int = 0
    error: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)

    def mark_sent(self) -> None:
        """Ghi nhận vừa gửi request đi: ``PENDING``/``FAILED`` (gửi lại) → ``SENT``."""
        if self.status not in (SyncStatus.PENDING, SyncStatus.FAILED):
            raise InvalidSyncStateError(f"Chỉ gửi được khi ở PENDING/FAILED (đang {self.status})")
        self.status = SyncStatus.SENT
        self.request_at = _now()

    def mark_acked(self, *, response_code: str | None, response_body: str | None) -> None:
        """Cổng CSDL Dược xác nhận: ``SENT`` → ``ACK``."""
        if self.status is not SyncStatus.SENT:
            raise InvalidSyncStateError(f"Chỉ ACK được khi ở SENT (đang {self.status})")
        self.status = SyncStatus.ACK
        self.response_at = _now()
        self.response_code = response_code
        self.response_body = response_body
        self.error = None

    def mark_failed(self, *, error: str, response_code: str | None = None) -> None:
        """Gửi lỗi / bị từ chối: ``SENT`` → ``FAILED``, tăng ``retry_count``."""
        if self.status is not SyncStatus.SENT:
            raise InvalidSyncStateError(f"Chỉ FAILED được khi ở SENT (đang {self.status})")
        self.status = SyncStatus.FAILED
        self.response_at = _now()
        self.response_code = response_code
        self.error = error
        self.retry_count += 1


class SyncRetryStatus(StrEnum):
    """Trạng thái của một việc gửi lại đang chờ (docs/13 mục D.4)."""

    PENDING = "PENDING"  # còn phải gửi lại, tới hạn thì relay lấy
    DEAD = "DEAD"  # hết số lần thử tự động — cần người xử lý


@dataclass(slots=True)
class NationalSyncRetryTask:
    """Việc **gửi lại** 1 payload lên CSDL Dược đang treo (docs/13 mục D.4).

    Không phải bản ghi audit — audit là :class:`NationalSyncLog` (mục D.2, chỉ giữ
    ``payload_hash``, không đổi). Đây là hàng đợi giao vận: giữ payload **thô** đúng
    khoảng thời gian nghĩa vụ liên thông (mục D.1 "đầy đủ, chính xác, kịp thời") **chưa**
    hoàn thành. Cổng ACK → dòng này bị xóa ngay, payload biến mất; không ACK → còn giữ để
    lần sau gửi lại được đúng nội dung cũ (cùng ``payload_hash`` với dòng audit).

    ``client_uuid`` unique theo tenant, trùng khóa idempotency của ``NationalSyncLog`` — 1
    bản ghi cần gửi chỉ có tối đa 1 việc gửi lại, không bao giờ nhân đôi.

    Số lần thử là **có hạn** (``attempt_count`` ≥ ``max_retries`` → ``DEAD``): gửi lại vô
    hạn vào một cổng đang từ chối là tự DDoS chính mình, và che mất việc cần người nhìn.
    """

    tenant_id: UUID
    branch_id: UUID
    sync_log_id: UUID
    payload_type: SyncPayloadType
    client_uuid: str
    payload: str
    status: SyncRetryStatus = SyncRetryStatus.PENDING
    attempt_count: int = 0
    next_attempt_at: datetime | None = None
    last_error: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)

    def is_due(self, now: datetime) -> bool:
        """Đã tới hạn gửi lại chưa (``DEAD`` thì không bao giờ)."""
        return self.status is SyncRetryStatus.PENDING and (
            self.next_attempt_at is None or self.next_attempt_at <= now
        )

    def lease_until(self, deadline: datetime) -> None:
        """Đẩy hạn kế tiếp ra ``deadline`` — chống 2 relay cùng cầm 1 việc.

        Relay đặt lease **trước** khi gọi cổng (I/O ngoài, có thể lâu) rồi mới ghi kết quả
        sau, nên không phải giữ transaction CSDL suốt lúc gọi mạng. Tiến trình chết giữa
        chừng: lease hết hạn, việc tự nổi lại — gửi lại là **at-least-once**, an toàn vì
        ``push_payload`` idempotent theo ``client_uuid``.
        """
        if self.status is not SyncRetryStatus.PENDING:
            raise InvalidSyncStateError(f"Chỉ giữ chỗ được việc PENDING (đang {self.status})")
        self.next_attempt_at = deadline

    def record_failure(
        self, *, error: str, now: datetime, base_backoff_seconds: float, max_retries: int
    ) -> bool:
        """Ghi 1 lần thử hỏng. Trả ``True`` nếu đã hẹn lần sau, ``False`` nếu đã ``DEAD``.

        Giãn cách theo cấp số nhân (``base * 2^(n-1)``) — cùng công thức
        :class:`~pharmacy_os.core.outbox.OutboxRelay` đang dùng, không phát minh kiểu backoff
        thứ hai trong cùng codebase.
        """
        if self.status is not SyncRetryStatus.PENDING:
            raise InvalidSyncStateError(f"Chỉ ghi nhận được việc PENDING (đang {self.status})")
        self.attempt_count += 1
        self.last_error = error
        if self.attempt_count >= max_retries:
            self.status = SyncRetryStatus.DEAD
            self.next_attempt_at = None
            return False
        backoff = base_backoff_seconds * 2 ** (self.attempt_count - 1)
        self.next_attempt_at = now + timedelta(seconds=backoff)
        return True


@dataclass(frozen=True, slots=True)
class ReturnedDrugItem:
    """Một dòng trong bảng danh mục thuốc nhận lại (Phụ lục XVIII, docs/13 mục C.6).

    ``description`` là chuỗi tự do (tên/dạng bào chế/nồng độ/quy cách/số ĐKLH) theo đúng cột gộp
    của mẫu giấy gốc — không tra `catalog` (mẫu pháp lý không yêu cầu, và cưỡng ép tra cứu sẽ vượt
    phạm vi mẫu gốc; xem docs/features/bien-ban-nhan-lai-pl-xviii/01_DECISIONS.md Bước 3).
    """

    description: str
    unit: str
    quantity: Decimal
    lot_no: str
    expiry_date: date
    condition_note: str
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantity", Decimal(self.quantity))
        if self.quantity <= 0:
            raise ValueError("Số lượng thuốc nhận lại phải > 0")


@dataclass(frozen=True, slots=True)
class LedgerBookSignature:
    """Xác nhận điện tử (Điều 15.1.d, hướng A) cho 1 sổ trong 1 ngày (docs/13 mục C.5).

    Phạm vi **cả sổ** trong ngày đó (mọi thuốc của ``book_type``) — khớp đúng phạm vi mà
    :func:`~pharmacy_os.modules.compliance.application.service.ComplianceService.export_daily_closure`
    kết xuất (bước 5). Không có ``drug_id`` (bản thiết kế gốc liệt kê nhầm cột này — xem
    docs/features/tt18-kiem-soat-dac-biet/02_DECISIONS_KY_SO.md Bước 2) và không có
    ``branch_id`` — sổ là hồ sơ theo cơ sở (tenant), không theo quầy, cùng nguyên tắc đã áp cho
    :class:`ControlledLedgerEntry`.

    Bất biến sau khi tạo, cùng nguyên tắc với :class:`ControlledLedgerEntry`/
    :class:`DrugReturnRecord` — ký lại một ngày đã ký là hành vi bị chặn ở tầng service (không
    phải ở đây), vì kiểm tra đó cần đọc CSDL (đã có chưa), việc entity thuần không tự làm được.
    """

    tenant_id: UUID
    book_type: LedgerBookType
    book_date: date
    content_sha256: str
    prev_hash: str | None
    signed_by_user_id: UUID
    signed_at: datetime = field(default_factory=_now)
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if len(self.content_sha256) != 64:
            raise ValueError("content_sha256 phải là chuỗi hex SHA-256 (64 ký tự)")
        if self.prev_hash is not None and len(self.prev_hash) != 64:
            raise ValueError("prev_hash phải là chuỗi hex SHA-256 (64 ký tự) nếu có")


@dataclass(slots=True)
class DrugReturnRecord:
    """Biên bản nhận lại thuốc GN/HT/TC (TT18 Điều 6.2 + Điều 12.1.d, Phụ lục XVIII).

    Bất biến sau khi tạo — không có phương thức sửa/xóa, cùng nguyên tắc với
    :class:`ControlledLedgerEntry` (hồ sơ tuân thủ, không phải dữ liệu tác nghiệp có thể chỉnh sửa).
    Không nối `drug_id`/`ControlledLedgerEntry` — mẫu giấy gốc không có cột đó (xem
    ``ReturnedDrugItem``).
    """

    tenant_id: UUID
    branch_id: UUID
    returner_name: str
    returner_address: str
    returner_id_number: str
    returner_id_issuer: str
    returner_id_issued_at: date
    returner_is_patient: bool
    receiving_pharmacist_name: str
    items: list[ReturnedDrugItem]
    handover_at: datetime
    handover_location: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("Biên bản nhận lại thuốc phải có ít nhất 1 dòng thuốc")
