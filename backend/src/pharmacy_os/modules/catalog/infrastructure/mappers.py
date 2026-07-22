"""Mapping between catalog ORM rows and domain entities."""

from __future__ import annotations

from uuid import UUID

from pharmacy_os.modules.catalog.domain import (
    ActiveIngredient,
    Drug,
    DrugIngredient,
    DrugUnit,
    RxClass,
)
from pharmacy_os.modules.catalog.infrastructure.models import (
    ActiveIngredientORM,
    DrugIngredientORM,
    DrugORM,
    DrugUnitORM,
)


def to_domain(row: DrugORM) -> Drug:
    drug = Drug(
        id=row.id,
        name=row.name,
        rx_class=RxClass(row.rx_class),
        base_unit=row.base_unit,
        registration_no=row.registration_no,
        atc_code=row.atc_code,
        form=row.form,
        strength=row.strength,
        barcode=row.barcode,
    )
    drug.units = [
        DrugUnit(id=u.id, unit_name=u.unit_name, factor=u.factor, is_sellable=u.is_sellable)
        for u in row.units
    ]
    drug.ingredients = [
        DrugIngredient(id=i.id, ingredient_id=i.ingredient_id, amount=i.amount, unit=i.unit)
        for i in row.ingredients
    ]
    return drug


def to_orm(drug: Drug, tenant_id: UUID) -> DrugORM:
    return DrugORM(
        id=drug.id,
        tenant_id=tenant_id,
        name=drug.name,
        rx_class=drug.rx_class.value,
        base_unit=drug.base_unit,
        registration_no=drug.registration_no,
        atc_code=drug.atc_code,
        form=drug.form,
        strength=drug.strength,
        barcode=drug.barcode,
        units=[
            DrugUnitORM(
                id=u.id,
                drug_id=drug.id,
                unit_name=u.unit_name,
                factor=u.factor,
                is_sellable=u.is_sellable,
            )
            for u in drug.units
        ],
        ingredients=[
            DrugIngredientORM(
                id=i.id,
                drug_id=drug.id,
                ingredient_id=i.ingredient_id,
                amount=i.amount,
                unit=i.unit,
            )
            for i in drug.ingredients
        ],
    )


def ingredient_to_domain(row: ActiveIngredientORM) -> ActiveIngredient:
    return ActiveIngredient(id=row.id, name=row.name, name_en=row.name_en)


def ingredient_to_orm(ingredient: ActiveIngredient) -> ActiveIngredientORM:
    return ActiveIngredientORM(id=ingredient.id, name=ingredient.name, name_en=ingredient.name_en)
