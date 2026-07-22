"""Catalog data-transfer objects (framework-free dataclasses)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from pharmacy_os.modules.catalog.domain import Drug, RxClass


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
