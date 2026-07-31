"""Kiểm kê theo ô — quy tắc domain (BERAS V2 Phase 11)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from pharmacy_os.modules.inventory.domain.counting import (
    CountError,
    CountStatus,
    StockCount,
)


def _phien() -> StockCount:
    return StockCount(tenant_id=uuid4(), branch_id=uuid4(), location_id=uuid4(), counted_by=uuid4())


# ─── Đếm ─────────────────────────────────────────────────────────────────────────


def test_dem_lai_cung_lo_thi_DE_khong_cong_don() -> None:
    """🔴 Người đếm lại một lô là người vừa phát hiện mình đếm sai.

    Cộng dồn biến một lần sửa lỗi thành một lần khai khống, và không có cách nào nhìn ra
    từ kết quả — 3 rồi 5 ra 8 trông y hệt một lô thật sự có 8.
    """
    p = _phien()
    lo = uuid4()
    p.dem(lo, Decimal("3"))
    p.dem(lo, Decimal("5"))
    assert len(p.lines) == 1
    assert p.lines[0].counted_qty == Decimal("5")


def test_dem_am_bi_tu_choi() -> None:
    p = _phien()
    with pytest.raises(CountError, match="không thể âm"):
        p.dem(uuid4(), Decimal("-1"))


def test_dem_0_duoc_phep() -> None:
    """Đếm ra 0 là một phát hiện, không phải một lỗi: ô trống mà sổ ghi còn hàng."""
    p = _phien()
    p.dem(uuid4(), Decimal("0"))
    assert p.lines[0].counted_qty == Decimal("0")


# ─── Nộp ─────────────────────────────────────────────────────────────────────────


def test_nop_chot_so_so_tai_thoi_diem_nop() -> None:
    p = _phien()
    a, b = uuid4(), uuid4()
    p.dem(a, Decimal("8"))
    p.dem(b, Decimal("2"))
    p.submit(so_ghi={a: Decimal("10"), b: Decimal("2")})

    assert p.status is CountStatus.CHO_DUYET
    assert p.submitted_at is not None
    assert p.lines[0].lech == Decimal("-2")  # thiếu 2
    assert p.lines[1].lech == Decimal("0")  # khớp


def test_lo_khong_co_trong_so_thi_so_ghi_bang_0() -> None:
    """Tìm thấy hàng hệ thống không biết — hợp lệ và thường gặp (hàng xếp nhầm ô)."""
    p = _phien()
    lo = uuid4()
    p.dem(lo, Decimal("6"))
    p.submit(so_ghi={})
    assert p.lines[0].system_qty == Decimal("0")
    assert p.lines[0].lech == Decimal("6")


def test_chua_nop_thi_lech_la_None_khong_phai_0() -> None:
    """🔴 Một con số chưa chốt phải NHÌN RA ĐƯỢC là chưa chốt.

    Trả 0 sẽ đọc y hệt "đã chốt và khớp" — đúng loại tín hiệu xanh chứng minh một mệnh đề
    khác với mệnh đề người đọc tưởng (kỷ luật #14).
    """
    p = _phien()
    p.dem(uuid4(), Decimal("4"))
    assert p.lines[0].system_qty is None
    assert p.lines[0].lech is None
    assert p.dong_lech == []


def test_nop_phien_rong_bi_tu_choi() -> None:
    p = _phien()
    with pytest.raises(CountError, match="chưa có dòng nào"):
        p.submit(so_ghi={})


def test_nop_hai_lan_bi_tu_choi() -> None:
    p = _phien()
    p.dem(uuid4(), Decimal("1"))
    p.submit(so_ghi={})
    with pytest.raises(CountError, match="đã nộp rồi"):
        p.submit(so_ghi={})


def test_da_nop_thi_khong_dem_them_duoc() -> None:
    """Sửa phiên đã nộp thì con số "sổ ghi bao nhiêu lúc nộp" mất nghĩa."""
    p = _phien()
    p.dem(uuid4(), Decimal("1"))
    p.submit(so_ghi={})
    with pytest.raises(CountError, match="mở phiên mới"):
        p.dem(uuid4(), Decimal("2"))


# ─── Duyệt / từ chối ─────────────────────────────────────────────────────────────


def test_duyet_chi_tra_ve_dong_THAT_SU_lech() -> None:
    """Dòng khớp không được sinh chuyển động ADJUST nào — ghi 0 vào sổ là rác."""
    p = _phien()
    a, b, c = uuid4(), uuid4(), uuid4()
    p.dem(a, Decimal("8"))  # sổ 10 → thiếu 2
    p.dem(b, Decimal("5"))  # sổ 5  → khớp
    p.dem(c, Decimal("3"))  # sổ 0  → thừa 3
    p.submit(so_ghi={a: Decimal("10"), b: Decimal("5")})

    nguoi_duyet = uuid4()
    lech = p.approve(by=nguoi_duyet)

    assert {d.batch_id for d in lech} == {a, c}
    assert p.status is CountStatus.DA_DUYET
    assert p.decided_by == nguoi_duyet
    assert p.decided_at is not None


def test_tu_choi_khong_dung_ton_kho() -> None:
    p = _phien()
    p.dem(uuid4(), Decimal("99"))
    p.submit(so_ghi={})
    p.reject(by=uuid4())
    assert p.status is CountStatus.TU_CHOI
    # Phiên ở lại trong sổ như một vết đã đếm — dòng không bị xoá.
    assert len(p.lines) == 1


def test_khong_duyet_duoc_phien_chua_nop() -> None:
    p = _phien()
    p.dem(uuid4(), Decimal("1"))
    with pytest.raises(CountError, match="đang chờ duyệt"):
        p.approve(by=uuid4())


def test_khong_duyet_hai_lan() -> None:
    p = _phien()
    p.dem(uuid4(), Decimal("1"))
    p.submit(so_ghi={})
    p.approve(by=uuid4())
    with pytest.raises(CountError, match="đang chờ duyệt"):
        p.approve(by=uuid4())
    with pytest.raises(CountError, match="đang chờ duyệt"):
        p.reject(by=uuid4())


def test_nguoi_dem_tu_duyet_ĐUOC_phep_nhung_luu_ca_hai_ten() -> None:
    """🔴 Cố ý KHÔNG chặn. Nhà thuốc nhỏ chỉ có một người.

    Chặn thì tính năng vô dụng với đúng nhóm khách hàng đông nhất. Cách xử lý là lưu cả hai
    tên để khi trùng nhau thì *nhìn ra được* — làm cho thấy được thay vì cấm.
    """
    ai_do = uuid4()
    p = StockCount(tenant_id=uuid4(), branch_id=uuid4(), location_id=uuid4(), counted_by=ai_do)
    p.dem(uuid4(), Decimal("1"))
    p.submit(so_ghi={})
    p.approve(by=ai_do)
    assert p.counted_by == p.decided_by == ai_do


def test_moc_thoi_gian_truyen_vao_duoc() -> None:
    """Cho phép truyền ``now`` — test không phụ thuộc đồng hồ thật (bài học 31/07: hai
    hàng ``created_at`` trùng nhau vì độ phân giải 1 giây của SQLite)."""
    p = _phien()
    p.dem(uuid4(), Decimal("1"))
    t = datetime(2026, 7, 31, 10, 0, tzinfo=UTC)
    p.submit(so_ghi={}, now=t)
    p.approve(by=uuid4(), now=t + timedelta(minutes=5))
    assert p.submitted_at == t
    assert p.decided_at == t + timedelta(minutes=5)
