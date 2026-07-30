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


# --- replace_ingredients: sửa hoạt chất nhập sai (§7ch) ----------------------


def _hc(amount: str = "500") -> DrugIngredient:
    return DrugIngredient(ingredient_id=uuid4(), amount=Decimal(amount), unit="mg")


def test_replace_ingredients_dat_lai_toan_bo_danh_sach() -> None:
    d = _drug()
    cu = _hc()
    d.add_ingredient(cu)
    moi_1, moi_2 = _hc("325"), _hc("200")
    d.replace_ingredients([moi_1, moi_2])
    assert {i.ingredient_id for i in d.ingredients} == {moi_1.ingredient_id, moi_2.ingredient_id}
    assert cu.ingredient_id not in {i.ingredient_id for i in d.ingredients}


def test_replace_ingredients_sua_nham_trong_MOT_luot() -> None:
    """🔴 Ca dùng thật: dược sĩ nhập sai hoạt chất, sửa lại cho đúng.

    Một lượt là điều đáng giá ở đây — làm hai lượt (xoá rồi thêm) thì tồn tại một khoảng
    thuốc mang danh sách sai theo cách khác, và trong khoảng đó cảnh báo dị ứng vẫn chạy.
    """
    d = _drug()
    sai = _hc()
    d.add_ingredient(sai)
    dung = _hc()
    d.replace_ingredients([dung])
    assert [i.ingredient_id for i in d.ingredients] == [dung.ingredient_id]


def test_replace_ingredients_danh_sach_rong_la_hop_le() -> None:
    """Băng gạc, khẩu trang, nhiệt kế đúng là không có hoạt chất nào.

    Domain không biết thuốc này là thuốc hay vật tư nên không chặn được ở đây — việc ghi
    vết "trước N, sau 0" thuộc tầng ứng dụng.
    """
    d = _drug()
    d.add_ingredient(_hc())
    d.replace_ingredients([])
    assert d.ingredients == []


def test_replace_ingredients_trung_hoat_chat_BI_TU_CHOI() -> None:
    d = _drug()
    trung = uuid4()
    with pytest.raises(DuplicateIngredientError):
        d.replace_ingredients(
            [
                DrugIngredient(ingredient_id=trung, amount=Decimal("500"), unit="mg"),
                DrugIngredient(ingredient_id=trung, amount=Decimal("250"), unit="mg"),
            ]
        )


def test_replace_ingredients_that_bai_thi_GIU_NGUYEN_danh_sach_cu() -> None:
    """🔴 Toàn-bộ-hoặc-không-gì. Áp dụng nửa vời một danh sách hoạt chất trên tính năng
    cảnh báo dị ứng còn tệ hơn từ chối hẳn: thuốc sẽ mang danh sách không ai chủ ý đặt."""
    d = _drug()
    cu = _hc()
    d.add_ingredient(cu)
    trung = uuid4()
    with pytest.raises(DuplicateIngredientError):
        d.replace_ingredients(
            [
                DrugIngredient(ingredient_id=trung, amount=Decimal("1"), unit="mg"),
                DrugIngredient(ingredient_id=trung, amount=Decimal("2"), unit="mg"),
            ]
        )
    assert [i.ingredient_id for i in d.ingredients] == [cu.ingredient_id]


def test_replace_ingredients_khong_dung_chung_list_voi_ben_goi() -> None:
    """Giữ tham chiếu tới list của bên gọi thì sửa list đó sau sẽ âm thầm sửa cả thuốc."""
    d = _drug()
    ds = [_hc()]
    d.replace_ingredients(ds)
    ds.append(_hc())
    assert len(d.ingredients) == 1


def test_replace_ingredients_giu_nguyen_ham_luong_va_don_vi() -> None:
    d = _drug()
    hc = DrugIngredient(ingredient_id=uuid4(), amount=Decimal("62.5"), unit="mg/ml")
    d.replace_ingredients([hc])
    assert d.ingredients[0].amount == Decimal("62.5")
    assert d.ingredients[0].unit == "mg/ml"
