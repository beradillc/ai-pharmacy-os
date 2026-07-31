"""Catalog data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.catalog.domain import (
    ActiveIngredient,
    Drug,
    DrugPriceRecord,
    RxClass,
)


@dataclass(slots=True)
class CreateIngredientInput:
    name: str
    name_en: str | None = None


@dataclass(slots=True)
class ActiveIngredientOutput:
    id: UUID
    name: str
    name_en: str | None

    @classmethod
    def of(cls, ingredient: ActiveIngredient) -> ActiveIngredientOutput:
        return cls(id=ingredient.id, name=ingredient.name, name_en=ingredient.name_en)


@dataclass(slots=True)
class DrugUnitInput:
    unit_name: str
    factor: Decimal
    is_sellable: bool = True


@dataclass(slots=True)
class DrugIngredientInput:
    ingredient_id: UUID
    amount: Decimal
    unit: str


@dataclass(slots=True)
class CreateDrugInput:
    name: str
    rx_class: RxClass
    base_unit: str
    registration_no: str | None = None
    atc_code: str | None = None
    form: str | None = None
    strength: str | None = None
    barcode: str | None = None
    sale_price: Decimal | None = None
    units: list[DrugUnitInput] = field(default_factory=list)
    ingredients: list[DrugIngredientInput] = field(default_factory=list)


@dataclass(slots=True)
class DrugUnitOutput:
    unit_name: str
    factor: Decimal
    is_sellable: bool


@dataclass(slots=True)
class DrugIngredientOutput:
    ingredient_id: UUID
    amount: Decimal
    unit: str


@dataclass(slots=True)
class DrugIngredientRef:
    """A drug's active ingredient resolved to both of its identities.

    Catalog is the single authority mapping a ``drug_id`` to its ingredients; the
    cross-module safety checks consume this pair because they key differently —
    clinical interaction rules match by ``name``, CRM allergies by ``ingredient_id``.
    """

    ingredient_id: UUID
    name: str


@dataclass(slots=True)
class PriceHistoryOutput:
    """Một dòng lịch sử giá cho tầng giao diện.

    Có ``changed_by``/``changed_at`` — khác ``DrugPriceChange`` của miền, vốn cố ý không
    biết ai và lúc nào. Xem ``DrugPriceRecord``.
    """

    id: UUID
    old_price: Decimal | None
    new_price: Decimal
    reason: str | None
    changed_by: UUID | None
    changed_at: datetime

    @classmethod
    def of(cls, record: DrugPriceRecord) -> PriceHistoryOutput:
        return cls(
            id=record.id,
            old_price=record.old_price,
            new_price=record.new_price,
            reason=record.reason,
            changed_by=record.changed_by,
            changed_at=record.changed_at,
        )


@dataclass(slots=True)
class DrugOutput:
    id: UUID
    name: str
    rx_class: str
    base_unit: str
    registration_no: str | None
    atc_code: str | None
    form: str | None
    strength: str | None
    barcode: str | None
    #: Giá bán lẻ một đơn vị lẻ, hoặc ``None`` khi chưa đặt giá — xem ``Drug.sale_price``.
    sale_price: Decimal | None
    prescription_required: bool
    units: list[DrugUnitOutput]
    ingredients: list[DrugIngredientOutput]

    @classmethod
    def of(cls, drug: Drug) -> DrugOutput:
        return cls(
            id=drug.id,
            name=drug.name,
            rx_class=drug.rx_class.value,
            base_unit=drug.base_unit,
            registration_no=drug.registration_no,
            atc_code=drug.atc_code,
            form=drug.form,
            strength=drug.strength,
            barcode=drug.barcode,
            sale_price=drug.sale_price,
            prescription_required=drug.is_prescription_required(),
            units=[
                DrugUnitOutput(unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
                for u in drug.units
            ],
            ingredients=[
                DrugIngredientOutput(ingredient_id=i.ingredient_id, amount=i.amount, unit=i.unit)
                for i in drug.ingredients
            ],
        )
