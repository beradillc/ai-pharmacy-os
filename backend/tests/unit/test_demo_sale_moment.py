"""Giờ hoá đơn demo không được rơi vào tương lai.

🔴 Sinh từ báo cáo thật 2026-07-29: Gấu Bông bán một đơn lúc 15h10, **doanh thu
tăng đúng**, nhưng đầu màn Hoá đơn thấy y nguyên ⇒ tưởng phần mềm không cập nhật.

Đo ra: đơn thật nằm ở **vị trí 7/14**, bị **6 hoá đơn demo có giờ trong tương
lai** (tới 16:30Z trong khi lúc đó là 08:13Z) đè lên trên, vì danh sách sắp
mới-nhất-trước.

Không phải lỗi phần mềm. Nhưng dữ liệu demo làm phần mềm **trông như hỏng** trước
mặt người dùng thì tệ ngang một lỗi thật — và khó chẩn đoán hơn nhiều, vì mọi cổng
đều xanh và API trả đúng.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from seeds.demo_pharmacy import _sale_moment


def test_hoa_don_hom_nay_khong_bao_gio_o_tuong_lai() -> None:
    now = datetime.now(UTC)
    for _ in range(300):
        assert _sale_moment(now.date()) < now


def test_hoa_don_hom_nay_van_nam_trong_ngay_hom_nay() -> None:
    now = datetime.now(UTC)
    for _ in range(300):
        assert _sale_moment(now.date()).date() == now.date()


def test_ngay_qua_khu_van_rai_deu_gio_lam_viec() -> None:
    """Ngày cũ giữ nguyên cách cũ — bản vá chỉ được chạm ngày hôm nay."""
    day = date.today() - timedelta(days=5)
    moments = [_sale_moment(day) for _ in range(300)]
    assert all(m.date() == day for m in moments)
    assert all(time(7, 0) <= m.timetz().replace(tzinfo=None) <= time(20, 59) for m in moments)
    # Có rải thật, không phải kẹt một giờ duy nhất.
    assert len({m.hour for m in moments}) >= 8
