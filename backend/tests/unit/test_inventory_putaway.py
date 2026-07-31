"""Quy tắc cất hàng vào vị trí và thứ tự lấy hàng (BERAS V2 Phase 2).

Hai tính chất tệp này canh, và cả hai là quyết định **nghiệp vụ** chứ không phải kỹ thuật:

* **bất biến hai sổ** — tổng đã xếp ô ≤ tồn của lô. Vỡ bất biến này nghĩa là màn hình lấy
  hàng chỉ người ta tới một ô không có hàng;
* **FEFO thắng, đường đi chỉ quyết khi HSD bằng nhau** (GĐ chốt 2026-07-31, Chain uỷ quyền).
  An toàn thuốc không đánh đổi lấy vài bước chân.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.inventory.domain import (
    ExceedsBatchOnHandError,
    InsufficientStockError,
    LocationNotUsableError,
    PickCandidate,
    allocate_from_locations,
    chua_xep_o,
    ensure_can_put_away,
    sort_pick_candidates,
)

D = Decimal


def _cho(*, path: str, pick: int, hsd: str, qty: str, lot: str = "L1") -> PickCandidate:
    return PickCandidate(
        location_id=uuid4(),
        location_path=path,
        pick_order=pick,
        batch_id=uuid4(),
        lot_no=lot,
        expiry_date=date.fromisoformat(hsd),
        quantity=D(qty),
    )


# ─── bất biến hai sổ ────────────────────────────────────────────────────────────


def test_xep_trong_pham_vi_ton_thi_duoc() -> None:
    ensure_can_put_away(dang_xep=D("30"), ton_cua_lo=D("100"), them=D("70"), o_dang_hoat_dong=True)


def test_xep_VUOT_ton_cua_lo_bi_tu_choi() -> None:
    """🔴 Vỡ bất biến này là màn lấy hàng chỉ người ta tới một ô không có hàng."""
    with pytest.raises(ExceedsBatchOnHandError):
        ensure_can_put_away(
            dang_xep=D("30"), ton_cua_lo=D("100"), them=D("71"), o_dang_hoat_dong=True
        )


def test_bat_bien_ap_tren_TONG_moi_o_khong_phai_tung_o() -> None:
    """Một lô trải nhiều ô là bình thường — chặn theo từng ô sẽ chặn nhầm nghiệp vụ đúng."""
    # đã xếp 90 ở các ô khác, còn 10; xếp thêm 10 vào ô mới ⇒ vừa đủ
    ensure_can_put_away(dang_xep=D("90"), ton_cua_lo=D("100"), them=D("10"), o_dang_hoat_dong=True)
    with pytest.raises(ExceedsBatchOnHandError):
        ensure_can_put_away(
            dang_xep=D("90"), ton_cua_lo=D("100"), them=D("11"), o_dang_hoat_dong=True
        )


def test_o_da_ngung_khong_cat_hang_vao_duoc() -> None:
    with pytest.raises(LocationNotUsableError):
        ensure_can_put_away(
            dang_xep=D("0"), ton_cua_lo=D("100"), them=D("1"), o_dang_hoat_dong=False
        )


def test_so_luong_khong_duong_bi_tu_choi() -> None:
    with pytest.raises(ValueError):
        ensure_can_put_away(
            dang_xep=D("0"), ton_cua_lo=D("100"), them=D("0"), o_dang_hoat_dong=True
        )


def test_hang_CHUA_XEP_O_la_hop_le_va_dem_duoc() -> None:
    """Hàng vừa nhận còn trên xe đẩy — giấu con số này là để sổ vị trí nói dối trong im lặng."""
    assert chua_xep_o(ton_cua_lo=D("100"), dang_xep=D("30")) == D("70")
    assert chua_xep_o(ton_cua_lo=D("100"), dang_xep=D("100")) == D("0")


def test_chua_xep_o_khong_bao_gio_am() -> None:
    """Nếu sổ đã lệch, hiện số âm chỉ làm người đọc mất phương hướng."""
    assert chua_xep_o(ton_cua_lo=D("10"), dang_xep=D("30")) == D("0")


# ─── FEFO thắng, đường đi chỉ quyết khi HSD bằng nhau ───────────────────────────


def test_FEFO_THANG_du_o_do_di_xa_hon() -> None:
    """🔴 Quyết định của GĐ: an toàn thuốc không đánh đổi lấy vài bước chân."""
    gan_nhung_han_xa = _cho(path="A/01", pick=1, hsd="2027-12-31", qty="100")
    xa_nhung_han_gan = _cho(path="Z/99", pick=99, hsd="2026-09-30", qty="100")

    xep = sort_pick_candidates([gan_nhung_han_xa, xa_nhung_han_gan])
    assert xep[0].location_path == "Z/99"


def test_HSD_BANG_NHAU_thi_di_gan_hon_thang() -> None:
    """Cùng hạn dùng thì không còn lý do an toàn nào để chọn — lúc đó đi gần hơn là đúng."""
    xa = _cho(path="Z/99", pick=99, hsd="2027-01-01", qty="50")
    gan = _cho(path="A/01", pick=1, hsd="2027-01-01", qty="50")

    xep = sort_pick_candidates([xa, gan])
    assert [c.location_path for c in xep] == ["A/01", "Z/99"]


def test_HSD_va_thu_tu_bang_nhau_thi_thu_tu_ON_DINH() -> None:
    """Hai lượt gọi không bao giờ được cho hai thứ tự khác nhau."""
    b = _cho(path="B/01", pick=5, hsd="2027-01-01", qty="10")
    a = _cho(path="A/01", pick=5, hsd="2027-01-01", qty="10")
    assert [c.location_path for c in sort_pick_candidates([b, a])] == ["A/01", "B/01"]
    assert [c.location_path for c in sort_pick_candidates([a, b])] == ["A/01", "B/01"]


# ─── chia hàng cho các chỗ ──────────────────────────────────────────────────────


def test_lay_du_o_mot_cho_thi_khong_dong_toi_cho_thu_hai() -> None:
    gan = _cho(path="A/01", pick=1, hsd="2026-06-30", qty="50")
    xa = _cho(path="Z/99", pick=9, hsd="2026-06-30", qty="50")
    kq = allocate_from_locations([gan, xa], D("30"))
    assert len(kq) == 1
    assert (kq[0][0].location_path, kq[0][1]) == ("A/01", D("30"))


def test_TRAI_NHIEU_O_khi_mot_cho_khong_du() -> None:
    """Người đi lấy phải biết phần còn lại ở đâu, không đứng trước một ô thiếu hàng."""
    han_gan = _cho(path="Z/99", pick=9, hsd="2026-06-30", qty="20")
    han_xa = _cho(path="A/01", pick=1, hsd="2027-06-30", qty="80")
    kq = allocate_from_locations([han_gan, han_xa], D("50"))
    assert [(c.location_path, q) for c, q in kq] == [("Z/99", D("20")), ("A/01", D("30"))]


def test_bo_qua_cho_co_so_luong_0() -> None:
    rong = _cho(path="A/01", pick=1, hsd="2026-01-01", qty="0")
    co = _cho(path="B/01", pick=9, hsd="2027-01-01", qty="10")
    kq = allocate_from_locations([rong, co], D("10"))
    assert [c.location_path for c, _ in kq] == ["B/01"]


def test_khong_du_hang_DA_XEP_O_thi_bao_thieu() -> None:
    """Thiếu ở đây KHÔNG có nghĩa kho hết hàng — có thể hàng còn nhưng chưa ai xếp vào ô."""
    with pytest.raises(InsufficientStockError):
        allocate_from_locations([_cho(path="A/01", pick=1, hsd="2027-01-01", qty="5")], D("6"))


def test_khong_co_cho_nao_thi_bao_thieu(  # noqa: D103
) -> None:
    with pytest.raises(InsufficientStockError):
        allocate_from_locations([], D("1"))
