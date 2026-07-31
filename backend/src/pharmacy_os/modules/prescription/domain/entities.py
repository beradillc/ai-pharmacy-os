"""Prescription aggregate: :class:`Prescription` with its items and lifecycle."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from pharmacy_os.modules.prescription.domain.exceptions import (
    EmptyPrescriptionError,
    InvalidPrescriptionImageError,
    InvalidPrescriptionStateError,
)

#: Định dạng ảnh chấp nhận được. Danh sách ĐÓNG, không đoán từ đuôi tệp: một chuỗi
#: ``content_type`` do máy khách gửi là thứ máy khách tự khai, nên nó phải khớp một
#: giá trị trong danh sách này chứ không phải "trông giống ảnh".
ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

#: Trần kích thước ảnh SAU khi giải mã base64, tính bằng byte. 2 MB.
#:
#: Con số này là thoả hiệp giữa hai thứ đo được: một ảnh 1600px JPEG chất lượng 0,7 —
#: đủ nét để đọc chữ viết tay trên đơn — nặng khoảng 200–400 KB, nên 2 MB rộng gấp năm
#: lần nhu cầu thật; còn phía trên, một ảnh thô 5 MB sẽ thành ~9 MB một dòng sau base64
#: → mã hoá → base64, và đó là ngưỡng làm hỏng `pg_dump`.
MAX_IMAGE_BYTES = 2 * 1024 * 1024


def _now() -> datetime:
    return datetime.now(UTC)


class PrescriptionStatus(StrEnum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    DISPENSED = "DISPENSED"
    REJECTED = "REJECTED"


class PrescriptionSource(StrEnum):
    MANUAL = "MANUAL"
    IMAGE = "IMAGE"
    EPRESCRIPTION = "EPRESCRIPTION"


@dataclass(slots=True)
class PrescriptionItem:
    """One prescribed drug line. ``dose``/``frequency``/``duration`` are free-text, as written."""

    drug_id: UUID
    quantity: Decimal
    dose: str
    frequency: str
    duration: str
    instructions: str | None = None
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        self.quantity = Decimal(self.quantity)
        if self.quantity <= 0:
            raise ValueError("Số lượng thuốc trong đơn phải > 0")


@dataclass(slots=True)
class Prescription:
    """A patient's prescription (aggregate root).

    Lifecycle: ``DRAFT`` → ``VALIDATED`` → ``DISPENSED``, or ``DRAFT``/``VALIDATED``
    → ``REJECTED``. Items are fixed at creation — this module does not support
    editing a prescription's drug list after intake.
    """

    tenant_id: UUID
    branch_id: UUID
    customer_id: UUID
    doctor_name: str
    source: PrescriptionSource = PrescriptionSource.MANUAL
    doctor_license: str | None = None
    diagnosis: str | None = None
    image_url: str | None = None
    """Địa chỉ ảnh đơn ở một kho NGOÀI hệ thống. Giữ nguyên, **không xoá** (kỷ luật #17):
    một deployment khác có thể đang trỏ tệp ngoài. Đường lưu-trong-CSDL dùng
    :attr:`image_data`, và hai thứ này độc lập nhau."""

    image_data: str | None = None
    """Ảnh đơn thuốc, **base64 của chính byte ảnh** (không phải data URL).

    Vì sao base64 chứ không phải byte thô: khoá mã hoá at-rest của dự án làm việc trên
    chuỗi (``crypto.encrypt(str) -> str``), và cột này dùng lại đúng ``EncryptedText`` đó.
    Viết một kiểu nhị phân mã hoá mới nghĩa là thêm một mặt phẳng mật mã thứ hai — chỗ
    tốn kém nhất để sai, và runbook xoay khoá sẽ phải biết về hai chỗ thay vì một.

    🔴 Đây là **dữ liệu cá nhân nhạy cảm** (Luật 91/2025): ảnh mang tên, tuổi, chẩn đoán,
    tên bác sĩ. Khác mọi PII đã xử lý trước nay, nó **không cắt nhỏ được** — không có cách
    nào che riêng phần chẩn đoán như đã che số điện thoại (ADR-0002). Quyền đọc vì thế
    tách riêng (``rx.image.read``) và mỗi lần đọc đều ghi vết."""

    image_content_type: str | None = None
    """``image/jpeg`` … — phải khớp :data:`ALLOWED_IMAGE_TYPES`."""

    status: PrescriptionStatus = PrescriptionStatus.DRAFT
    validated_by: UUID | None = None
    rejection_reason: str | None = None
    items: list[PrescriptionItem] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=_now)

    def _ensure_status(self, *allowed: PrescriptionStatus) -> None:
        if self.status not in allowed:
            raise InvalidPrescriptionStateError(
                f"Đơn không ở trạng thái cho phép (đang {self.status}, cần {allowed})"
            )

    def add_item(self, item: PrescriptionItem) -> None:
        self._ensure_status(PrescriptionStatus.DRAFT)
        self.items.append(item)

    def attach_image(self, image_data: str, content_type: str) -> None:
        """Gắn ảnh đơn thuốc đã chụp. Ghi đè ảnh cũ nếu có — chụp lại là ca dùng thật.

        Cho phép ghi đè có chủ ý: người đứng quầy chụp trượt, chụp thiếu góc, chụp ngược
        sáng là chuyện thường ngày. Bắt họ xoá rồi chụp lại qua hai thao tác chỉ tạo ra
        một trạng thái trung gian **không có ảnh nào** trên một đơn thuốc kê đơn.

        Không ràng buộc theo ``status``: một đơn đã ``DISPENSED`` vẫn có thể cần bổ sung
        ảnh gốc mà lúc bán chưa kịp chụp, và từ chối lúc đó là để lại một đơn ETC **không
        có căn cứ** mãi mãi — trái đúng Điều 74 Luật Dược, thứ tính năng này sinh ra để thoả.

        Raises :class:`InvalidPrescriptionImageError` nếu định dạng không nằm trong
        :data:`ALLOWED_IMAGE_TYPES`, ảnh rỗng, base64 hỏng, hoặc vượt
        :data:`MAX_IMAGE_BYTES` sau khi giải mã.
        """
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise InvalidPrescriptionImageError(
                f"Định dạng ảnh không nhận: {content_type}. "
                f"Chỉ nhận {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
            )
        try:
            # `validate=True` bắt buộc: không có nó, base64 im lặng BỎ QUA mọi ký tự lạ
            # rồi trả về một chuỗi byte ngắn hơn — một ảnh hỏng sẽ đi qua cổng này và chỉ
            # lộ ra lúc dược sĩ mở lên xem, có thể là nhiều tháng sau.
            raw = base64.b64decode(image_data, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise InvalidPrescriptionImageError("Ảnh không phải base64 hợp lệ") from exc
        if not raw:
            raise InvalidPrescriptionImageError("Ảnh rỗng")
        if len(raw) > MAX_IMAGE_BYTES:
            raise InvalidPrescriptionImageError(
                f"Ảnh {len(raw) // 1024} KB vượt trần {MAX_IMAGE_BYTES // 1024} KB"
            )
        self.image_data = image_data
        self.image_content_type = content_type

    def validate(self, validated_by: UUID) -> None:
        """Pharmacist approval: ``DRAFT`` → ``VALIDATED``. Requires at least one item."""
        self._ensure_status(PrescriptionStatus.DRAFT)
        if not self.items:
            raise EmptyPrescriptionError("Không thể xác thực đơn thuốc rỗng")
        self.validated_by = validated_by
        self.status = PrescriptionStatus.VALIDATED

    def reject(self, reason: str) -> None:
        """Reject — allowed from ``DRAFT`` (đơn không hợp lệ) or ``VALIDATED`` (rủi ro)."""
        self._ensure_status(PrescriptionStatus.DRAFT, PrescriptionStatus.VALIDATED)
        self.rejection_reason = reason
        self.status = PrescriptionStatus.REJECTED

    def dispense(self) -> None:
        """Cấp phát: ``VALIDATED`` → ``DISPENSED``."""
        self._ensure_status(PrescriptionStatus.VALIDATED)
        self.status = PrescriptionStatus.DISPENSED
