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

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pharmacy_os.core.db.base import Base, PkUuidMixin, TimestampMixin


class CustomerORM(PkUuidMixin, TimestampMixin, Base):
    """Customer/patient master record — tenant-scoped (not branch-scoped, like ``drugs``)."""

    __tablename__ = "customers"

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    dob: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(16))
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    national_id_hash: Mapped[str | None] = mapped_column(String(128))

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


class CustomerAllergyORM(PkUuidMixin, Base):
    __tablename__ = "customer_allergies"

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("active_ingredients.id"), index=True, nullable=False
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    customer: Mapped[CustomerORM] = relationship(back_populates="allergies")


class CustomerConditionORM(PkUuidMixin, Base):
    __tablename__ = "customer_conditions"

    customer_id: Mapped[UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), index=True
    )
    condition_code: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

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
