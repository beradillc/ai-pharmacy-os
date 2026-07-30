"""`build_plan` — quyết định chèn dòng nào khi vá `drug_ingredients` (§7cf).

Lệnh backfill **ghi vào CSDL Chain đang dùng thật** (`nt650v2`, 595 hoá đơn), nên phần
quyết định được tách thành hàm thuần để kiểm được từng tính chất mà không cần CSDL. Hai
tính chất đáng sợ nhất, và là lý do file này tồn tại:

* **không được ghi đè dòng đã có** — dòng đó có thể do dược sĩ nhập tay với hàm lượng
  thật, đè bằng `1` là làm dữ liệu tệ đi;
* **không được tự tạo hoạt chất còn thiếu** — `active_ingredients` không có `tenant_id`,
  thêm một dòng ở đó là thêm dữ liệu tham chiếu cho **mọi** nhà thuốc.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from seeds.backfill_drug_ingredients import _Drug, build_plan
from seeds.drug_ingredient_map import DRUG_INGREDIENTS

PARACETAMOL = UUID("00000000-0000-0000-0000-0000000000a1")
CAFEIN = UUID("00000000-0000-0000-0000-0000000000a2")
IBUPROFEN = UUID("00000000-0000-0000-0000-0000000000a3")

DANH_MUC = {"Paracetamol": PARACETAMOL, "Cafein": CAFEIN, "Ibuprofen": IBUPROFEN}


def _thuoc(ten: str, *, unit: str = "viên") -> _Drug:
    return _Drug(id=uuid4(), name=ten, base_unit=unit)


def test_noi_thuoc_mot_hoat_chat() -> None:
    t = _thuoc("Paracetamol 500mg")
    plan = build_plan([t], DANH_MUC, set())
    assert [(r.drug_id, r.ingredient_id) for r in plan.rows] == [(t.id, PARACETAMOL)]


def test_noi_thuoc_nhieu_hoat_chat() -> None:
    """Panadol Extra = Paracetamol + Cafein ⇒ hai dòng, không phải một."""
    t = _thuoc("Panadol Extra")
    plan = build_plan([t], DANH_MUC, set())
    assert {r.ingredient_id for r in plan.rows} == {PARACETAMOL, CAFEIN}


def test_bien_duoc_ten_khong_nhac_hoat_chat_van_noi_duoc() -> None:
    """🔴 Chính lý do tính năng dị ứng cần bảng ánh xạ: `Alaxan` không chứa chữ nào của
    `Paracetamol`, nên mọi cách khớp theo tên đều bỏ sót nó."""
    t = _thuoc("Alaxan")
    plan = build_plan([t], DANH_MUC, set())
    assert {r.ingredient_id for r in plan.rows} == {IBUPROFEN, PARACETAMOL}


def test_dong_da_co_thi_BO_QUA_khong_chen_trung() -> None:
    """🔴 Bảng `drug_ingredients` KHÔNG có ràng buộc unique trên (drug_id, ingredient_id) —
    CSDL sẽ nhận dòng trùng mà không kêu. Việc khử trùng nằm ở đúng đây."""
    t = _thuoc("Paracetamol 500mg")
    plan = build_plan([t], DANH_MUC, {(t.id, PARACETAMOL)})
    assert plan.rows == []
    assert plan.da_co == 1


def test_chay_lai_lan_hai_khong_chen_gi_them() -> None:
    """Tính chất an-toàn-khi-chạy-lại, phát biểu đúng như cách lệnh được dùng thật."""
    t = _thuoc("Panadol Extra")
    lan_1 = build_plan([t], DANH_MUC, set())
    assert len(lan_1.rows) == 2
    sau_lan_1 = {(r.drug_id, r.ingredient_id) for r in lan_1.rows}
    lan_2 = build_plan([t], DANH_MUC, sau_lan_1)
    assert lan_2.rows == []
    assert lan_2.da_co == 2


def test_noi_mot_phan_thi_chi_chen_phan_con_thieu() -> None:
    """CSDL đã vá dở — chèn đúng dòng còn thiếu, không đụng dòng đã có."""
    t = _thuoc("Panadol Extra")
    plan = build_plan([t], DANH_MUC, {(t.id, PARACETAMOL)})
    assert [r.ingredient_id for r in plan.rows] == [CAFEIN]
    assert plan.da_co == 1


def test_hoat_chat_khong_co_trong_danh_muc_thi_BAO_chu_khong_tu_tao() -> None:
    """🔴 Không tự tạo hoạt chất: `active_ingredients` là dữ liệu tham chiếu TOÀN HỆ THỐNG
    (không có `tenant_id`), và tên có thể trùng khác chính tả với dòng đã có."""
    t = _thuoc("Smecta")  # cần "Diosmectit", cố ý không có trong DANH_MUC
    plan = build_plan([t], DANH_MUC, set())
    assert plan.rows == []
    assert plan.thieu_hoat_chat == {"Smecta": ["Diosmectit"]}


def test_thuoc_ngoai_bang_anh_xa_duoc_liet_ke_khong_im_lang() -> None:
    """3 vật tư + 7 mã chờ Chain quyết. Chúng KHÔNG phải lỗi, nhưng phải nhìn thấy được —
    im lặng ở đây thì không ai biết còn 7 quyết định đang treo."""
    plan = build_plan([_thuoc("Khẩu trang y tế 4 lớp"), _thuoc("Oresol")], DANH_MUC, set())
    assert plan.rows == []
    assert sorted(plan.ngoai_bang) == ["Khẩu trang y tế 4 lớp", "Oresol"]


def test_don_vi_lay_theo_tung_thuoc_khong_dung_chung_mot_hang_so() -> None:
    plan = build_plan(
        [_thuoc("Paracetamol 500mg", unit="viên"), _thuoc("Smecta", unit="gói")],
        DANH_MUC | {"Diosmectit": uuid4()},
        set(),
    )
    assert {r.unit for r in plan.rows} == {"viên", "gói"}


def test_bang_anh_xa_khong_nhac_ba_vat_tu() -> None:
    """Canh chính bảng dữ liệu: vật tư có hoạt chất là sai về nghiệp vụ."""
    for vat_tu in ("Băng gạc y tế", "Khẩu trang y tế 4 lớp", "Nhiệt kế điện tử"):
        assert vat_tu not in DRUG_INGREDIENTS


def test_bang_anh_xa_khong_co_hoat_chat_lap_trong_cung_mot_thuoc() -> None:
    """Trùng trong bảng ánh xạ sẽ thành hai dòng y hệt trong CSDL — bảng không có unique."""
    for ten_thuoc, ds in DRUG_INGREDIENTS.items():
        assert len(ds) == len(set(ds)), ten_thuoc
