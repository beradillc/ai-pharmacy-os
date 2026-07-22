from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.catalog.domain import (
    ActiveIngredient,
    Drug,
    DrugIngredient,
    DrugUnit,
    DuplicateIngredientError,
    DuplicateUnitError,
    InvalidIngredientError,
    RxClass,
)


def _drug() -> Drug:
    return Drug(name="Paracetamol 500mg", rx_class=RxClass.OTC, base_unit="viên")


def test_add_unit_and_convert() -> None:
    d = _drug()
    d.add_unit(DrugUnit(unit_name="vỉ", factor=Decimal("10")))
    d.add_unit(DrugUnit(unit_name="hộp", factor=Decimal("100")))
    assert d.to_base_quantity(Decimal("2"), "vỉ") == Decimal("20")
    assert d.to_base_quantity(Decimal("1"), "hộp") == Decimal("100")
    assert d.to_base_quantity(Decimal("5"), "viên") == Decimal("5")


def test_duplicate_unit_rejected() -> None:
    d = _drug()
    d.add_unit(DrugUnit(unit_name="vỉ", factor=Decimal("10")))
    with pytest.raises(DuplicateUnitError):
        d.add_unit(DrugUnit(unit_name="vỉ", factor=Decimal("12")))


def test_unit_matching_base_rejected() -> None:
    d = _drug()
    with pytest.raises(DuplicateUnitError):
        d.add_unit(DrugUnit(unit_name="viên", factor=Decimal("1")))


def test_unknown_unit_conversion_raises() -> None:
    d = _drug()
    with pytest.raises(ValueError):
        d.to_base_quantity(Decimal("1"), "thùng")


def test_prescription_required_flag() -> None:
    assert not Drug(name="A", rx_class=RxClass.OTC, base_unit="viên").is_prescription_required()
    assert Drug(name="B", rx_class=RxClass.ETC, base_unit="viên").is_prescription_required()
    assert Drug(name="C", rx_class=RxClass.CONTROLLED, base_unit="v").is_prescription_required()


def test_zero_factor_rejected() -> None:
    with pytest.raises(ValueError):
        DrugUnit(unit_name="x", factor=Decimal("0"))


def test_active_ingredient_requires_name() -> None:
    with pytest.raises(InvalidIngredientError):
        ActiveIngredient(name="   ")


def test_active_ingredient_optional_english_name() -> None:
    ing = ActiveIngredient(name="Paracetamol", name_en="Acetaminophen")
    assert ing.name_en == "Acetaminophen"


def test_drug_ingredient_amount_must_be_positive() -> None:
    with pytest.raises(InvalidIngredientError):
        DrugIngredient(ingredient_id=uuid4(), amount=Decimal("0"), unit="mg")


def test_drug_ingredient_unit_required() -> None:
    with pytest.raises(InvalidIngredientError):
        DrugIngredient(ingredient_id=uuid4(), amount=Decimal("500"), unit="  ")


def test_add_ingredient_combination_drug() -> None:
    """A drug can carry more than one active ingredient (combination product)."""
    d = _drug()
    amoxicillin = uuid4()
    clavulanic_acid = uuid4()
    d.add_ingredient(DrugIngredient(ingredient_id=amoxicillin, amount=Decimal("500"), unit="mg"))
    d.add_ingredient(
        DrugIngredient(ingredient_id=clavulanic_acid, amount=Decimal("125"), unit="mg")
    )
    assert {i.ingredient_id for i in d.ingredients} == {amoxicillin, clavulanic_acid}


def test_duplicate_ingredient_rejected() -> None:
    d = _drug()
    ingredient_id = uuid4()
    d.add_ingredient(DrugIngredient(ingredient_id=ingredient_id, amount=Decimal("500"), unit="mg"))
    with pytest.raises(DuplicateIngredientError):
        d.add_ingredient(
            DrugIngredient(ingredient_id=ingredient_id, amount=Decimal("250"), unit="mg")
        )
