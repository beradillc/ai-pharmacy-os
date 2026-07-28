"""SQLAlchemy models for crm. Cross-dialect (Postgres + SQLite for tests).

``CustomerAllergyORM.ingredient_id`` carries a real FK to ``active_ingredients``
(catalog's global reference table) — a deliberate, first-of-its-kind cross-module
DB constraint in this codebase. It stays safe for ``module-independence``: the FK
is a plain string table name in the DDL, so it needs no Python import of catalog's
ORM classes, and ``active_ingredients`` is global (not tenant-scoped) so there is no
cross-tenant risk. Unlike ``sales.SaleLine.drug_id``/``prescription...drug_id``
(deliberately un-FK'd, tenant-scoped, historical snapshots), an ingredient
reference here benefits from real integrity since allergies must name a real
ingredient. SQLite (the test harness) doesn't enforce FKs by default, but
``core.db.session.build_engine`` turns on ``PRAGMA foreign_keys=ON`` per
connection for SQLite, so this constraint is exercised in tests too, not just
on live Postgres. ``CrmService.add_allergy`` catches the resulting
``IntegrityError`` and translates it to a 404 — see that module for why.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pharmacy_os.core.db.base import Base, PkUuidMixin, TimestampMixin
from pharmacy_os.core.db.encrypted_types import EncryptedText


class CustomerORM(PkUuidMixin, TimestampMixin, Base):
    """Customer/patient master record — tenant-scoped (not branch-scoped, like ``drugs``)."""

    __tablename__ = "customers"

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    """Encrypted at rest since 2026-07-28 (migration ``0035``).

    **Alphabetical paging was given up to get here, deliberately** — Chain chose that
    trade-off after it was put in front of them, and this docstring exists so nobody
    later "fixes" the ordering by decrypting the column again.

    Ciphertext sorts randomly, and no blind index restores order (a fingerprint
    preserves *equality*, never *order*). ``list()`` therefore orders by ``created_at``
    now. What made the trade acceptable: pharmacies look customers up by **phone** far
    more than by name, and that path is untouched — ``phone_fingerprint`` still answers
    exact lookups. What tipped it: a patient's name sitting in plaintext travels inside
    every database dump, i.e. outside the pharmacy, where Luật BVDLCN 91/2025 applies
    and an ordering convenience does not."""

    phone: Mapped[str | None] = mapped_column(EncryptedText)
    """Encrypted at rest. Lookup survives via :attr:`phone_fingerprint` — the reason
    the blind index exists at all."""

    phone_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    """Deterministic HMAC of the normalised phone, so ``find_by_phone`` still works
    against an encrypted column. Kept in step with ``phone`` by the repository, which
    is the only writer. ``NULL`` when the deployment has no index key — lookups then
    fall back to comparing ``phone`` directly, which is correct while encryption is
    off and during a backfill."""

    dob: Mapped[date | None] = mapped_column(Date)
    """Not encrypted: a ``date`` column would have to become text, losing the type and
    any future age query, for a weaker piece of PII than the phone. Deferred with the
    reason recorded, not overlooked."""

    gender: Mapped[str | None] = mapped_column(EncryptedText)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    national_id: Mapped[str | None] = mapped_column(EncryptedText)
    """Số CCCD/hộ chiếu — mã hoá at-rest từ 2026-07-28 (migration ``0036``, audit B-06).

    **Cột này từng tên là ``national_id_hash`` và KHÔNG hề băm gì cả** — client gửi gì
    lưu nấy, dạng rõ. Cái tên là một nửa của lỗi, không phải chuyện thẩm mỹ: bất kỳ ai
    đọc lược đồ, viết DPIA, hay trả lời thanh tra câu *"CCCD lưu thế nào"* đều sẽ trả
    lời **"đã băm"** — một bảo đảm sai, phát ra từ chính tên cột.

    Chọn **mã hoá** chứ không **băm** vì số định danh phải **đọc lại được**: nó đi vào
    biên bản nhận lại thuốc và các biểu mẫu có giá trị pháp lý. Một giá trị đã băm thì
    không in ra biểu mẫu được.

    Tiền lệ nội bộ quyết định hướng này, không phải sở thích: ``compliance`` đã mã hoá
    ``drug_return_records.returner_id_number`` từ trước — **cùng một loại dữ liệu**, và
    hai module không được đối xử khác nhau với nó."""
    anonymised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    allergies: Mapped[list[CustomerAllergyORM]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    conditions: Mapped[list[CustomerConditionORM]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    history: Mapped[list[CustomerMedicationHistoryORM]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    consents: Mapped[list[CustomerConsentORM]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class CustomerConsentORM(PkUuidMixin, Base):
    """One consent decision, appended and never updated.

    Deliberately a history table rather than a flag on ``customers``: an inspection
    asks "was there consent on the day that data was read", which a single boolean
    cannot answer. Carries the evidence Luật 91/2025 Điều 9 requires — when, which
    staff account, from which IP, against which version of the terms.
    """

    __tablename__ = "customer_consents"

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    granted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    terms_version: Mapped[str] = mapped_column(String(32), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column()
    client_ip: Mapped[str | None] = mapped_column(String(45))

    customer: Mapped[CustomerORM] = relationship(back_populates="consents")


class CustomerAllergyORM(PkUuidMixin, Base):
    __tablename__ = "customer_allergies"

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("active_ingredients.id"), index=True, nullable=False
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(EncryptedText)
    """Dữ liệu sức khoẻ (docs/14) — mã hoá at-rest.

    ``ingredient_id`` ngay trên KHÔNG mã hoá được: nó là khoá ngoại tới
    ``active_ingredients`` và là thứ ``find_allergy_alerts`` so khớp. Nghĩa là sự thật
    y tế cốt lõi ("dị ứng hoạt chất nào") vẫn nằm dạng rõ — nói thẳng ra ở đây thay vì
    để báo cáo ngầm hiểu là đã mã hoá xong dữ liệu dị ứng."""

    customer: Mapped[CustomerORM] = relationship(back_populates="allergies")


class CustomerConditionORM(PkUuidMixin, Base):
    __tablename__ = "customer_conditions"

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    condition_code: Mapped[str] = mapped_column(EncryptedText, nullable=False)
    """Mã ICD-10 = chẩn đoán bệnh nền, dữ liệu sức khoẻ nhạy cảm nhất trong bảng này."""

    note: Mapped[str | None] = mapped_column(EncryptedText)

    customer: Mapped[CustomerORM] = relationship(back_populates="conditions")


class CustomerMedicationHistoryORM(PkUuidMixin, Base):
    """Minimal ref-only history row — ``drug_id`` is a cross-module reference,
    deliberately **not** a FK, matching ``sales.SaleLine.drug_id``/
    ``prescription...drug_id`` (drugs are tenant-scoped catalog data; a history row
    must stay valid even if the referenced drug is later archived/deleted).
    """

    __tablename__ = "customer_medication_history"

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    drug_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    ref_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    customer: Mapped[CustomerORM] = relationship(back_populates="history")
