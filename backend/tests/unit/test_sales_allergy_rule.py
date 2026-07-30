"""Cổng xác nhận dị ứng lúc hoàn tất bán (domain thuần).

Quyết định Đ-6 (Chain, 2026-07-30): **cảnh báo + buộc xác nhận có ghi vết**, KHÔNG
chặn cứng. Đ-7: cảnh báo hiện ngay khi thêm thuốc vào đơn.

🔴 **Sales KHÔNG khớp dị ứng.** Việc khớp giỏ hàng với dị ứng của khách là của
``clinical`` (``find_allergy_alerts``) — đã có từ trước. Sales chỉ nhận **phán quyết**
qua :class:`AllergyRisk` rồi quyết một câu duy nhất: *đơn này có được hoàn tất không*.
Nên ở đây chỉ test cổng xác nhận, không test phép khớp.
"""

from __future__ import annotations

import pytest

from pharmacy_os.modules.sales.domain import (
    AllergyAcknowledgementRequiredError,
    AllergyRisk,
    ensure_allergy_acknowledged,
)

LY_DO = "Bác sĩ đã chỉ định, khách dùng nhiều lần không sao"


# --- Không có gì phải xác nhận ------------------------------------------------


def test_don_khong_gan_khach_thi_khong_can_xac_nhan() -> None:
    """``risk is None`` = đơn không ghi tên khách, hoặc hồ sơ khách đã mất.

    Bán vãng lai OTC hợp lệ không có khách — không được vì thế mà chặn bán.
    """
    ensure_allergy_acknowledged(None, None)  # không ném


def test_khach_khong_co_di_ung_thi_khong_can_xac_nhan() -> None:
    ensure_allergy_acknowledged(AllergyRisk(consent_granted=True, conflict_count=0), None)


def test_khach_chua_dong_y_cho_xem_du_lieu_suc_khoe_thi_van_ban_duoc() -> None:
    """🔴 Không có đồng ý ⇒ phép kiểm KHÔNG CHẠY, và vẫn phải bán được.

    Từ chối bán vì khách chưa đồng ý cho xử lý dữ liệu sức khoẻ là **phạt khách vì
    họ thực hiện quyền của mình** (Luật 91/2025 Điều 9), mà lại không có xung đột
    nào được biết là tồn tại. Quầy được cho biết phép kiểm không chạy — bằng
    ``consent_granted=False`` — chứ không bị chặn.
    """
    ensure_allergy_acknowledged(AllergyRisk(consent_granted=False, conflict_count=0), None)


# --- Có xung đột thì phải có lý do -------------------------------------------


def test_co_xung_dot_ma_khong_ghi_ly_do_thi_bi_chan() -> None:
    risk = AllergyRisk(consent_granted=True, conflict_count=1, worst_severity="SEVERE")
    with pytest.raises(AllergyAcknowledgementRequiredError):
        ensure_allergy_acknowledged(risk, None)


@pytest.mark.parametrize("trong", ["", "   ", "\t\n"])
def test_ly_do_toan_khoang_trang_khong_tinh_la_xac_nhan(trong: str) -> None:
    """Đ-6 đòi người bán chịu trách nhiệm **bằng chữ**; khoảng trắng không phải chữ.

    Không có phép kiểm này thì cổng chỉ cách vô dụng đúng một lần bấm phím trống.
    """
    risk = AllergyRisk(consent_granted=True, conflict_count=1, worst_severity="MILD")
    with pytest.raises(AllergyAcknowledgementRequiredError):
        ensure_allergy_acknowledged(risk, trong)


def test_ghi_ly_do_thi_ban_duoc() -> None:
    risk = AllergyRisk(consent_granted=True, conflict_count=2, worst_severity="SEVERE")
    ensure_allergy_acknowledged(risk, LY_DO)  # không ném


def test_thong_diep_loi_noi_ro_so_luong_va_muc_do_nang_nhat() -> None:
    """Quầy phải biết **bao nhiêu** và **nặng cỡ nào** chỉ từ thông điệp — POS hiện
    nguyên văn khi hộp thoại xác nhận bị bỏ qua."""
    risk = AllergyRisk(consent_granted=True, conflict_count=3, worst_severity="SEVERE")
    with pytest.raises(AllergyAcknowledgementRequiredError) as err:
        ensure_allergy_acknowledged(risk, None)
    assert "3" in str(err.value)
    assert "SEVERE" in str(err.value)


def test_thieu_muc_do_van_chan_va_van_doc_duoc() -> None:
    """``worst_severity=None`` xảy ra nếu clinical trả mức độ lạ. Vẫn phải chặn —
    không biết nặng cỡ nào thì càng phải hỏi người bán, không được cho đi im lặng."""
    risk = AllergyRisk(consent_granted=True, conflict_count=1)
    with pytest.raises(AllergyAcknowledgementRequiredError) as err:
        ensure_allergy_acknowledged(risk, None)
    assert "không rõ mức độ" in str(err.value)
