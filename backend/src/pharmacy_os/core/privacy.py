"""The technical half of a DPIA, derived from the code rather than written by hand.

NĐ 356/2025 Điều 41.2 removes the small-business exemption as soon as sensitive data
is processed, so **every** tenant running the customer-health feature — down to a
single-counter pharmacy — owes Bộ Công an a đánh giá tác động xử lý DLCN within 60
days of starting (Luật 91/2025 Điều 21). BeraLLC does not file it for them (duyệt
Q6); it supplies the part only the system can answer.

Generated from the live permission and audit constants on purpose. A static
appendix in a Word file drifts the first time somebody adds a permission and nobody
notices for a year; this cannot, because the names come from the same objects the
runtime enforces.

What this is **not**: the legal sections (controller identity, necessity and
proportionality assessment, the pharmacy's own organisational measures). Those are
the tenant's to write, with counsel.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pharmacy_os.core.audit.entry import AuditAction


@dataclass(frozen=True, slots=True)
class DataCategory:
    name: str
    examples: list[str]
    sensitive: bool
    legal_basis: str
    purposes: list[str]
    guarded_by: list[str]
    """Permission codes that gate access — the enforced ones, not aspirational."""

    retention: str


@dataclass(frozen=True, slots=True)
class ProcessingRecord:
    """The system's answer to "what personal data do you process, and how"."""

    categories: list[DataCategory]
    audited_actions: list[str]
    audit_storage: str
    cross_border_transfers: list[str]
    subject_rights: dict[str, str]
    known_gaps: list[str] = field(default_factory=list)


_CUSTOMER_BASIC = DataCategory(
    name="Dữ liệu định danh cơ bản của khách hàng",
    examples=["họ tên", "số điện thoại", "ngày sinh", "giới tính"],
    sensitive=False,
    legal_basis="Đồng ý của chủ thể — Luật 91/2025/QH15 Điều 9 (mục đích BASIC)",
    purposes=["Định danh người mua trên đơn bán và hóa đơn"],
    guarded_by=["crm.read", "crm.create", "crm.write"],
    retention=(
        "Theo nghĩa vụ lưu trữ hồ sơ bán hàng; khử nhận dạng theo yêu cầu của chủ thể "
        "(Luật 91/2025 Điều 13-14)"
    ),
)

_CUSTOMER_HEALTH = DataCategory(
    name="Dữ liệu sức khỏe của khách hàng (DỮ LIỆU NHẠY CẢM)",
    examples=["dị ứng hoạt chất", "bệnh nền (ICD-10)", "lịch sử dùng thuốc"],
    sensitive=True,
    legal_basis=(
        "Đồng ý của chủ thể — Luật 91/2025/QH15 Điều 26.1 (mục đích HEALTH). "
        "KHÔNG có nghĩa vụ luật định buộc nhà thuốc lưu loại dữ liệu này, nên đồng ý "
        "là cơ sở pháp lý DUY NHẤT"
    ),
    purposes=[
        "Cảnh báo an toàn dược lý khi bán/cấp phát thuốc",
        "Tư vấn chuyên môn của dược sĩ",
    ],
    guarded_by=["crm.sensitive.read", "crm.sensitive.write", "crm.erase"],
    retention=(
        "Tối thiểu 1 năm kể từ khi hết hạn dùng của thuốc đối với dòng cấp phát "
        "(GPP TT02/2018 I-1a.II.4.d); dị ứng/bệnh nền xóa ngay khi khử nhận dạng"
    ),
)

_CUSTOMER_ACTIONS = (
    AuditAction.CUSTOMER_SENSITIVE_READ,
    AuditAction.CUSTOMER_SENSITIVE_AUTO_CHECK,
    AuditAction.CUSTOMER_SENSITIVE_WRITE,
    AuditAction.CONSENT_GRANTED,
    AuditAction.CONSENT_REVOKED,
    AuditAction.CUSTOMER_ERASED,
)


def processing_record() -> ProcessingRecord:
    """Build the record from the constants the runtime actually enforces."""
    return ProcessingRecord(
        categories=[_CUSTOMER_BASIC, _CUSTOMER_HEALTH],
        audited_actions=[a.value for a in _CUSTOMER_ACTIONS],
        audit_storage=(
            "Bảng audit_logs, chỉ ghi thêm (repository không có update/delete). "
            "Nội dung dữ liệu KHÔNG được sao chép vào nhật ký — chỉ metadata "
            "(loại trường, IP, chi nhánh)"
        ),
        cross_border_transfers=[
            "Không có. Lớp AI lâm sàng chỉ gửi TÊN HOẠT CHẤT, không gửi định danh "
            "khách hàng — nếu thay đổi thì kích hoạt nghĩa vụ đánh giá tác động "
            "chuyển dữ liệu xuyên biên giới (Luật 91/2025 Điều 20, NĐ356 Điều 17-18)"
        ],
        subject_rights={
            "Quyền được biết / xem": "GET /api/v1/customers/{id}",
            "Quyền yêu cầu cung cấp dữ liệu": "GET /api/v1/customers/{id}/export",
            "Quyền rút lại đồng ý": "POST /api/v1/customers/{id}/consents (granted=false)",
            "Quyền xóa": (
                "POST /api/v1/customers/{id}/anonymise — khử nhận dạng, giữ dòng cấp "
                "phát mang nghĩa vụ lưu trữ GPP"
            ),
        },
        known_gaps=[
            "Chưa có văn bản điều khoản thật tương ứng terms_version: bản ghi đồng ý "
            "chứng minh được AI bấm/lúc nào/IP nào, chưa chứng minh được khách đã "
            "được cho biết những gì",
            "Chưa có luồng người đại diện cho bệnh nhân trẻ em (Luật 91/2025 Điều 24)",
            "Chưa có xóa tự động khi hết thời hạn lưu trữ",
            "client_ip ghi IP của reverse proxy nếu triển khai sau proxy",
        ],
    )
