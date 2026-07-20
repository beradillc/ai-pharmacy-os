from decimal import Decimal

import pytest

from pharmacy_os.modules.catalog.domain import Drug, DrugUnit, DuplicateUnitError, RxClass


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
