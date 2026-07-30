"""Sổ tích luỹ và quà thưởng (Đ-9, Chain chốt 2026-07-30 — thay Đ-5).

Mỗi test dưới đây canh một câu Chain đã nói, không phải một nhánh mã.

Đ-9 đổi cấu trúc: *"cứ mỗi khi đủ 2 triệu, 1 hộp khẩu trang, trong cùng 1 năm"* —
một bậc **lặp lại**, thay cho hai mốc một-lần-mỗi-năm của Đ-5. Nên phần thưởng
chuyển từ **tập hợp mốc** sang **số đếm**.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from pharmacy_os.modules.crm.domain.loyalty import (
    REWARD_STEP,
    AccrualEntry,
    DuplicateAccrualError,
    LoyaltyError,
    RewardAlreadyGrantedError,
    RewardGrant,
    RewardNotEarnedError,
    YearlyLoyalty,
    boxes_earned,
)

NOW = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)


def _so(customer_id: UUID | None = None) -> YearlyLoyalty:
    return YearlyLoyalty(customer_id=customer_id or uuid4(), year=2026)


def _cong(so: YearlyLoyalty, tien: str, order_id: UUID | None = None) -> AccrualEntry:
    e = AccrualEntry(
        customer_id=so.customer_id,
        order_id=order_id or uuid4(),
        amount=Decimal(tien),
        occurred_at=NOW,
    )
    so.accrue(e)
    return e


def _qua(so: YearlyLoyalty, sequence: int | None = None) -> RewardGrant:
    return RewardGrant(
        customer_id=so.customer_id,
        year=so.year,
        sequence=sequence if sequence is not None else so.boxes_granted + 1,
        granted_at=NOW,
    )


# --- Bậc thưởng: LẶP LẠI, không phải hai mốc một lần -------------------------


def test_bac_thuong_la_hai_trieu() -> None:
    """Canh chính con số Chain nói, để đổi bậc là phải sửa test."""
    assert int(REWARD_STEP) == 2_000_000


def test_chua_du_hai_trieu_thi_chua_co_hop_nao() -> None:
    assert boxes_earned(Decimal("1999999")) == 0


def test_dung_hai_trieu_la_dat_bac_khong_phai_hon_hai_trieu() -> None:
    """ "Đủ 2 triệu" là >= 2 triệu. Khách tích đúng 2.000.000 đ phải được hộp."""
    assert boxes_earned(Decimal("2000000")) == 1


def test_bac_lap_lai_khong_co_tran() -> None:
    """🔴 Đây là chỗ Đ-9 khác Đ-5. Đ-5: 11 triệu vẫn chỉ 2 mốc. Đ-9: lặp lại."""
    assert boxes_earned(Decimal("4000000")) == 2
    assert boxes_earned(Decimal("5900000")) == 2  # chưa tới 6 triệu
    assert boxes_earned(Decimal("6000000")) == 3
    assert boxes_earned(Decimal("25000000")) == 12  # khách cao nhất đo được ở nt650v2


def test_tich_luy_am_tra_ve_khong_chu_khong_am() -> None:
    """Sổ bị đảo nhiều hơn cộng. Một phép đếm âm không có nghĩa gì ở quầy."""
    assert boxes_earned(Decimal("-5000000")) == 0


# --- Sổ chỉ ghi thêm ---------------------------------------------------------


def test_cong_cung_mot_don_hai_lan_bi_chan() -> None:
    """🔴 Sự kiện bán hàng ĐƯỢC GỬI LẠI khi outbox thử lại (rủi ro R-1).

    Không chặn thì một đơn 3 triệu cộng hai lần là khách chạm bậc bằng tiền
    không có thật — và nhà thuốc mất quà cho một giao dịch không tồn tại.
    """
    so = _so()
    don = uuid4()
    _cong(so, "500000", don)
    with pytest.raises(DuplicateAccrualError):
        _cong(so, "500000", don)
    assert so.accrued == Decimal("500000")


def test_huy_don_thi_DAO_but_toan_chu_khong_xoa() -> None:
    """Rủi ro R-2. Lịch sử phải còn nguyên để trả lời "tháng trước có đủ bậc không"."""
    so = _so()
    e = _cong(so, "2200000")
    assert so.pending_boxes() == 1

    dao = so.reverse(e.id, at=NOW)
    assert dao.amount == Decimal("-2200000")
    assert so.accrued == Decimal("0")
    assert so.pending_boxes() == 0
    # Cả hai dòng còn nguyên — không dòng nào bị xoá.
    assert len(so.entries) == 2


def test_khong_dao_hai_lan_cung_mot_but_toan() -> None:
    so = _so()
    e = _cong(so, "800000")
    so.reverse(e.id, at=NOW)
    with pytest.raises(LoyaltyError):
        so.reverse(e.id, at=NOW)


def test_khong_dao_mot_but_toan_dao() -> None:
    so = _so()
    e = _cong(so, "800000")
    dao = so.reverse(e.id, at=NOW)
    with pytest.raises(LoyaltyError):
        so.reverse(dao.id, at=NOW)


def test_but_toan_bang_khong_bi_tu_choi() -> None:
    with pytest.raises(LoyaltyError):
        AccrualEntry(customer_id=uuid4(), order_id=uuid4(), amount=Decimal("0"), occurred_at=NOW)


def test_thoi_diem_phai_co_mui_gio() -> None:
    """Thiếu múi giờ là cách một đơn lúc 23h ngày 31/12 rơi nhầm sang năm sau."""
    with pytest.raises(LoyaltyError):
        AccrualEntry(
            customer_id=uuid4(),
            order_id=uuid4(),
            amount=Decimal("1000"),
            occurred_at=datetime(2026, 12, 31, 23, 0),  # noqa: DTZ001 — cố ý
        )


# --- Trao quà ----------------------------------------------------------------


def test_chua_du_bac_thi_khong_trao_duoc() -> None:
    so = _so()
    _cong(so, "1500000")
    with pytest.raises(RewardNotEarnedError):
        so.grant(_qua(so))


def test_trao_lien_tiep_theo_so_hop_duoc_huong() -> None:
    """Khách tích 6 triệu được 3 hộp — trao đủ 3, không hơn."""
    so = _so()
    _cong(so, "6000000")
    assert so.pending_boxes() == 3
    for _ in range(3):
        so.grant(_qua(so))
    assert so.boxes_granted == 3
    assert so.pending_boxes() == 0


def test_khong_trao_vuot_so_duoc_huong() -> None:
    """🔴 Chặn cả trường hợp gọi nhiều lần liên tiếp khi chỉ còn đúng một hộp."""
    so = _so()
    _cong(so, "2500000")  # 1 hộp
    so.grant(_qua(so))
    with pytest.raises(RewardAlreadyGrantedError):
        so.grant(_qua(so, sequence=2))


def test_so_thu_tu_phai_lien_tuc() -> None:
    """Không có phép kiểm này thì hai lượt trao đồng thời cùng ghi số 3, và sổ mất
    khả năng trả lời "đã trao mấy hộp" — cùng họ với rủi ro cộng trùng order_id."""
    so = _so()
    _cong(so, "6000000")  # 3 hộp
    so.grant(_qua(so, sequence=1))
    with pytest.raises(RewardAlreadyGrantedError):
        so.grant(_qua(so, sequence=3))  # nhảy số
    with pytest.raises(RewardAlreadyGrantedError):
        so.grant(_qua(so, sequence=1))  # trùng số đã trao
    so.grant(_qua(so, sequence=2))  # đúng thứ tự thì đi được
    assert so.boxes_granted == 2


def test_mua_them_sinh_ra_hop_moi() -> None:
    """Bậc lặp lại: nhận xong hộp 1, mua thêm tới 4 triệu thì có hộp 2."""
    so = _so()
    _cong(so, "2000000")
    so.grant(_qua(so))
    assert so.pending_boxes() == 0
    _cong(so, "2000000")
    assert so.pending_boxes() == 1


# --- Đ-9: trả hàng thì KHÔNG thu hồi quà -------------------------------------


def test_tra_hang_sau_khi_nhan_qua_thi_KHONG_bi_doi_lai() -> None:
    """🔴 Đ-9 (Chain chốt 30/07): không thu hồi, khoá ở mức đã trao.

    Hộp khẩu trang đã cho thì không đòi lại, và cũng không ghi nợ — ``pending_boxes``
    chạm sàn 0 chứ không đi âm.
    """
    so = _so()
    e = _cong(so, "2200000")
    so.grant(_qua(so))
    assert so.boxes_granted == 1

    so.reverse(e.id, at=NOW)  # khách trả hàng, tích luỹ về 0
    assert boxes_earned(so.accrued) == 0
    assert so.boxes_granted == 1  # vẫn còn vết đã trao
    assert so.pending_boxes() == 0  # KHÔNG âm


def test_sau_khi_tra_hang_phai_mua_lai_tu_dau_moi_co_hop_moi() -> None:
    """Hệ quả của "khoá ở mức đã trao": khách đã nhận 2 hộp rồi trả gần hết hàng,
    mua thêm một lúc vẫn chưa có hộp nào — đúng ý Chain, không phải lỗi."""
    so = _so()
    e = _cong(so, "4000000")  # 2 hộp
    so.grant(_qua(so))
    so.grant(_qua(so))
    so.reverse(e.id, at=NOW)  # về 0, nhưng đã trao 2

    _cong(so, "4000000")  # được hưởng 2, đã trao 2
    assert so.pending_boxes() == 0
    _cong(so, "2000000")  # tổng 6 triệu ⇒ được hưởng 3
    assert so.pending_boxes() == 1
