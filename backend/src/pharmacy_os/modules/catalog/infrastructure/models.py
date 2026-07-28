"""SQLAlchemy models for catalog. Cross-dialect (Postgres + SQLite for tests)."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pharmacy_os.core.db.base import Base, PkUuidMixin, TimestampMixin


class AtcCodeORM(Base):
    __tablename__ = "atc_codes"

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[int] = mapped_column(nullable=False, default=5)


class DrugORM(PkUuidMixin, TimestampMixin, Base):
    __tablename__ = "drugs"
    __table_args__ = (
        # SĐK phải duy nhất theo tenant (docs/13_COMPLIANCE_SPEC.md mục F). NULL được phép
        # trùng nhiều lần (chuẩn SQL: NULL != NULL) — thuốc chưa có SĐK không bị chặn.
        UniqueConstraint("tenant_id", "registration_no", name="uq_drugs_tenant_registration_no"),
    )

    tenant_id: Mapped[UUID] = mapped_column(index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rx_class: Mapped[str] = mapped_column(String(16), nullable=False)
    base_unit: Mapped[str] = mapped_column(String(32), nullable=False)
    registration_no: Mapped[str | None] = mapped_column(String(64))
    atc_code: Mapped[str | None] = mapped_column(String(16), index=True)
    form: Mapped[str | None] = mapped_column(String(64))
    strength: Mapped[str | None] = mapped_column(String(64))
    barcode: Mapped[str | None] = mapped_column(String(64), index=True)
    #: Giá bán lẻ trên một đơn vị lẻ. Numeric(18,2) — cùng độ rộng mọi cột tiền khác.
    sale_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)

    units: Mapped[list[DrugUnitORM]] = relationship(
        back_populates="drug",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    ingredients: Mapped[list[DrugIngredientORM]] = relationship(
        back_populates="drug",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class DrugUnitORM(PkUuidMixin, Base):
    __tablename__ = "drug_units"

    drug_id: Mapped[UUID] = mapped_column(ForeignKey("drugs.id", ondelete="CASCADE"), index=True)
    unit_name: Mapped[str] = mapped_column(String(32), nullable=False)
    factor: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    is_sellable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    drug: Mapped[DrugORM] = relationship(back_populates="units")


class ActiveIngredientORM(PkUuidMixin, Base):
    """Global active-ingredient reference (docs/03 ``active_ingredients``), not tenant-scoped."""

    __tablename__ = "active_ingredients"
    __table_args__ = (
        # Dedup key for find_by_name — global reference data, one row per distinct ingredient.
        UniqueConstraint("name", name="uq_active_ingredients_name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[str | None] = mapped_column(String(255))


class DrugIngredientORM(PkUuidMixin, Base):
    """Dosage strength of one active ingredient within a drug (docs/03 ``drug_ingredients``)."""

    __tablename__ = "drug_ingredients"

    drug_id: Mapped[UUID] = mapped_column(ForeignKey("drugs.id", ondelete="CASCADE"), index=True)
    ingredient_id: Mapped[UUID] = mapped_column(
        ForeignKey("active_ingredients.id"), index=True, nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)

    drug: Mapped[DrugORM] = relationship(back_populates="ingredients")
