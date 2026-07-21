"""Compliance entities: national drug record and controlled-substance ledger.

See docs/13_COMPLIANCE_SPEC.md for the legal traceability of every field below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.compliance.domain.exceptions import NotControlledSubstanceError


def _now() -> datetime:
    return datetime.now(UTC)


class ControlledSubstanceCategory(StrEnum):
    """Phân loại thuốc kiểm soát đặc biệt (TT 20/2017 Điều 3 khoản 1-6). Xem docs/13 mục C.1.

    Phạm vi module chỉ áp dụng cơ sở bán lẻ — TT20/2017 còn có thuốc phóng xạ/thuốc độc/
    danh mục cấm cho loại hình cơ sở khác, ngoài phạm vi enum này.
    """

    GAY_NGHIEN = "GAY_NGHIEN"  # gây nghiện
    HUONG_THAN = "HUONG_THAN"  # hướng thần
    TIEN_CHAT = "TIEN_CHAT"  # tiền chất dùng làm thuốc
    PHOI_HOP_GN = "PHOI_HOP_GN"  # dạng phối hợp chứa gây nghiện
    PHOI_HOP_HT = "PHOI_HOP_HT"  # dạng phối hợp chứa hướng thần
    PHOI_HOP_TC = "PHOI_HOP_TC"  # dạng phối hợp chứa tiền chất
    NONE = "NONE"  # không thuộc diện kiểm soát — mặc định


class LedgerDirection(StrEnum):
    """Chiều giao dịch trong Sổ theo dõi xuất/nhập/tồn (Phụ lục VIII, TT 20/2017)."""

    NHAP = "NHAP"
    XUAT = "XUAT"


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
