"""Sơ đồ kho — quy tắc miền thuần.

Ba tính chất tệp này canh, và cả ba đều là chỗ dễ làm sai theo cách im lặng:

* **thứ bậc là ràng buộc thứ tự, không phải ràng buộc đủ tầng** — nhà thuốc nhỏ chỉ dùng
  Kho → Kệ là chuyện thường, bắt tạo Khu rỗng cho đủ tầng là bắt nhập dữ liệu giả;
* **mã bất biến, tên đổi được** — đổi mã sẽ buộc viết lại đường dẫn cả cây con;
* **chuẩn hoá mã** — nhãn dán trên kệ được gõ lại bằng tay, `a01` và `A01` phải là một chỗ.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from pharmacy_os.modules.location.domain import (
    InvalidLocationCodeError,
    InvalidLocationNestingError,
    Location,
    LocationHasChildrenError,
    LocationKind,
    normalize_code,
)

TENANT = uuid4()
BRANCH = uuid4()


def _kho(code: str = "KHO1") -> Location:
    return Location.create_root(tenant_id=TENANT, branch_id=BRANCH, code=code)


# ─── chuẩn hoá mã ───────────────────────────────────────────────────────────────


def test_ma_duoc_viet_hoa_va_bo_khoang_trang() -> None:
    assert normalize_code("  a01 ") == "A01"


def test_ma_rong_bi_tu_choi() -> None:
    with pytest.raises(InvalidLocationCodeError):
        normalize_code("   ")


def test_ma_chua_dau_gach_cheo_bi_tu_choi() -> None:
    """`/` là ký tự ngăn cách đường dẫn — cho vào mã thì đường dẫn không tách ngược được."""
    with pytest.raises(InvalidLocationCodeError):
        normalize_code("A/01")


def test_ma_qua_dai_bi_tu_choi() -> None:
    with pytest.raises(InvalidLocationCodeError):
        normalize_code("X" * 33)


# ─── thứ bậc ────────────────────────────────────────────────────────────────────


def test_kho_chua_duoc_khu_ke_o() -> None:
    kho = _kho()
    for kind in (LocationKind.ZONE, LocationKind.SHELF, LocationKind.BIN):
        assert kho.kind.can_contain(kind)


def test_BO_TANG_thi_duoc__ke_nam_thang_trong_kho() -> None:
    """Nhà thuốc nhỏ chỉ có Kho → Kệ. Bắt tạo Khu rỗng cho đủ tầng là bắt nhập dữ liệu giả."""
    kho = _kho()
    ke = kho.create_child(kind=LocationKind.SHELF, code="A01")
    assert ke.path == "KHO1/A01"


def test_DAO_TANG_thi_khong__khong_dat_khu_trong_o() -> None:
    kho = _kho()
    o = kho.create_child(kind=LocationKind.BIN, code="01")
    with pytest.raises(InvalidLocationNestingError):
        o.create_child(kind=LocationKind.ZONE, code="A")


def test_khong_dat_duoc_hai_tang_ngang_nhau() -> None:
    kho = _kho()
    ke = kho.create_child(kind=LocationKind.SHELF, code="A01")
    with pytest.raises(InvalidLocationNestingError):
        ke.create_child(kind=LocationKind.SHELF, code="A02")


# ─── đường dẫn ──────────────────────────────────────────────────────────────────


def test_duong_dan_ghep_theo_ca_cay() -> None:
    kho = _kho()
    khu = kho.create_child(kind=LocationKind.ZONE, code="A")
    ke = khu.create_child(kind=LocationKind.SHELF, code="A01")
    o = ke.create_child(kind=LocationKind.BIN, code="03")
    assert o.path == "KHO1/A/A01/03"


def test_duong_dan_dung_ma_DA_CHUAN_HOA() -> None:
    kho = _kho()
    ke = kho.create_child(kind=LocationKind.SHELF, code=" a01 ")
    assert ke.path == "KHO1/A01"


def test_is_descendant_of_dung_tien_to_co_dau_ngan_cach() -> None:
    """🔴 Không so tiền tố trần: 'KHO1/A1' KHÔNG nằm dưới 'KHO1/A'."""
    kho = _kho()
    khu_a = kho.create_child(kind=LocationKind.ZONE, code="A")
    khu_a1 = kho.create_child(kind=LocationKind.ZONE, code="A1")
    ke = khu_a.create_child(kind=LocationKind.SHELF, code="A01")

    assert ke.is_descendant_of(khu_a)
    assert not khu_a1.is_descendant_of(khu_a)


def test_khong_phai_con_cua_chinh_no() -> None:
    kho = _kho()
    assert not kho.is_descendant_of(kho)


# ─── đổi tên · thứ tự lấy hàng · ngừng hoạt động ────────────────────────────────


def test_doi_ten_KHONG_doi_ma_va_duong_dan() -> None:
    kho = _kho()
    ke = kho.create_child(kind=LocationKind.SHELF, code="A01", name="Kệ thuốc ho")
    ke.rename("Kệ kháng sinh")
    assert ke.name == "Kệ kháng sinh"
    assert ke.code == "A01"
    assert ke.path == "KHO1/A01"


def test_thu_tu_lay_hang_dat_duoc_va_KHONG_suy_ra_tu_ma() -> None:
    """Kệ A01 và A02 có thể đối lưng nhau qua một lối đi — chỉ người xếp kho biết."""
    kho = _kho()
    ke = kho.create_child(kind=LocationKind.SHELF, code="A01", pick_order=7)
    assert ke.pick_order == 7
    ke.set_pick_order(2)
    assert ke.pick_order == 2


def test_ngung_hoat_dong_khi_CON_CHO_CON_bi_tu_choi() -> None:
    """Ngừng cha mà để con lại tạo ra ô vẫn nhận hàng dưới một kệ đã khai tử."""
    ke = _kho().create_child(kind=LocationKind.SHELF, code="A01")
    with pytest.raises(LocationHasChildrenError):
        ke.deactivate(active_children=2)
    assert ke.is_active is True


def test_ngung_hoat_dong_khi_khong_con_con() -> None:
    ke = _kho().create_child(kind=LocationKind.SHELF, code="A01")
    ke.deactivate(active_children=0)
    assert ke.is_active is False


def test_khong_them_duoc_cho_moi_duoi_vi_tri_da_ngung() -> None:
    ke = _kho().create_child(kind=LocationKind.SHELF, code="A01")
    ke.deactivate(active_children=0)
    with pytest.raises(InvalidLocationNestingError):
        ke.create_child(kind=LocationKind.BIN, code="01")


def test_mo_lai_duoc() -> None:
    ke = _kho().create_child(kind=LocationKind.SHELF, code="A01")
    ke.deactivate(active_children=0)
    ke.reactivate()
    assert ke.is_active is True


def test_kho_luon_la_goc() -> None:
    kho = _kho()
    assert kho.parent_id is None
    assert kho.kind is LocationKind.WAREHOUSE
    assert kho.path == "KHO1"


def test_con_thua_ke_tenant_va_chi_nhanh_cua_cha() -> None:
    """Không nhận tenant/chi nhánh từ bên gọi: đó là đường để một vị trí lạc sang cơ sở khác."""
    kho = _kho()
    o = kho.create_child(kind=LocationKind.BIN, code="01")
    assert (o.tenant_id, o.branch_id) == (TENANT, BRANCH)
