"""SQLAlchemy models for prescription. Cross-dialect (Postgres + SQLite for tests)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pharmacy_os.core.db.base import Base, PkUuidMixin, TenantScopedMixin, TimestampMixin
from pharmacy_os.core.db.encrypted_types import EncryptedText


class PrescriptionORM(PkUuidMixin, TenantScopedMixin, TimestampMixin, Base):
    __tablename__ = "prescriptions"

    customer_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    doctor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    doctor_license: Mapped[str | None] = mapped_column(String(64), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    #: 🔴 MÃ HOÁ AT-REST. Ảnh đơn thuốc mang tên, tuổi, chẩn đoán, tên bác sĩ — dữ liệu cá
    #: nhân **nhạy cảm** theo Luật 91/2025. Dùng lại đúng `EncryptedText` và key ring đã
    #: có, nên runbook xoay khoá không phải biết thêm một chỗ thứ hai.
    #:
    #: Nội dung là base64 của chính byte ảnh (KHÔNG phải data URL): tiền tố `data:` là
    #: thứ trình duyệt cần, không phải thứ kho dữ liệu cần, và lưu nó đi là mời người đọc
    #: sau tin rằng cột này an toàn để nhét thẳng vào `src`.
    image_data: Mapped[str | None] = mapped_column(EncryptedText, nullable=True)
    image_content_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    validated_by: Mapped[UUID | None] = mapped_column(nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    items: Mapped[list[PrescriptionItemORM]] = relationship(
        back_populates="prescription",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PrescriptionItemORM(PkUuidMixin, Base):
    __tablename__ = "prescription_items"

    prescription_id: Mapped[UUID] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE"), index=True
    )
    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    dose: Mapped[str] = mapped_column(String(200), nullable=False)
    frequency: Mapped[str] = mapped_column(String(200), nullable=False)
    duration: Mapped[str] = mapped_column(String(200), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    prescription: Mapped[PrescriptionORM] = relationship(back_populates="items")
