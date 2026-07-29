"""Sổ tích luỹ và mốc thưởng (Đ-5, Chain chốt 2026-07-29).

Mỗi test dưới đây canh một câu Chain đã nói, không phải một nhánh mã.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from pharmacy_os.modules.crm.domain.loyalty import (
    AccrualEntry,
    DuplicateAccrualError,
    LoyaltyError,
    RewardAlreadyGrantedError,
    RewardGrant,
    RewardNotEarnedError,
    RewardTier,
    YearlyLoyalty,
    tiers_reached,
)

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


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


# --- Mốc: cộng dồn, không thay thế -------------------------------------------


def test_chua_du_mot_trieu_thi_chua_co_moc_nao() -> None:
    assert tiers_reached(Decimal("999999")) == frozenset()


def test_dung_mot_trieu_la_dat_moc_khong_phai_hon_mot_trieu() -> None:
    """Biên là ">=", không phải ">". Khách tích đúng 1.000.000 đ mà bị nói "chưa
    đủ" thì không ai giải thích nổi."""
    assert tiers_reached(Decimal("1000000")) == {RewardTier.ONE_MILLION}


def test_dat_ba_trieu_duoc_CA_HAI_moc() -> None:
    """🔴 Chain chốt: "Cả hai — bịch rồi tới hộp".

    Đây là chỗ dễ cài sai nhất: viết `if >= 3tr: moc3 elif >= 1tr: moc1` là mất
    quà mốc 1 triệu của người mua nhiều nhất.
    """
    assert tiers_reached(Decimal("3000000")) == {
        RewardTier.ONE_MILLION,
        RewardTier.THREE_MILLION,
    }


def test_mua_rat_nhieu_van_chi_hai_moc_do() -> None:
    """ "Một lần mỗi mốc, mỗi năm" — 11 triệu không sinh ra mốc thứ ba."""
    assert len(tiers_reached(Decimal("11000000"))) == 2


# --- Sổ chỉ ghi thêm ---------------------------------------------------------


def test_cong_cung_mot_don_hai_lan_bi_chan() -> None:
    """🔴 Sự kiện bán hàng ĐƯỢC GỬI LẠI khi outbox thử lại (rủi ro R-1).

    Không chặn thì một đơn 3 triệu cộng hai lần là khách chạm mốc bằng tiền
    không có thật — và nhà thuốc mất quà cho một giao dịch không tồn tại.
    """
    so = _so()
    don = uuid4()
    _cong(so, "500000", don)
    with pytest.raises(DuplicateAccrualError):
        _cong(so, "500000", don)
    assert so.accrued == Decimal("500000")


def test_huy_don_thi_DAO_but_toan_chu_khong_xoa() -> None:
    """Rủi ro R-2. Lịch sử phải còn nguyên để trả lời "tháng trước có đủ mốc không"."""
    so = _so()
    e = _cong(so, "1200000")
    assert so.pending_tiers() == {RewardTier.ONE_MILLION}

    dao = so.reverse(e.id, at=NOW)
    assert dao.amount == Decimal("-1200000")
    assert so.accrued == Decimal("0")
    assert so.pending_tiers() == frozenset()
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


def _qua(so: YearlyLoyalty, tier: RewardTier) -> RewardGrant:
    return RewardGrant(customer_id=so.customer_id, year=so.year, tier=tier, granted_at=NOW)


def test_chua_du_moc_thi_khong_trao_duoc() -> None:
    so = _so()
    _cong(so, "900000")
    with pytest.raises(RewardNotEarnedError):
        so.grant(_qua(so, RewardTier.ONE_MILLION))


def test_mot_moc_chi_trao_MOT_LAN_moi_nam() -> None:
    """🔴 Đây là câu "một lần mỗi mốc, mỗi năm" của Chain, đặt ở domain.

    Đặt ở giao diện thì hai thu ngân ở hai máy cùng bấm là trao hai lần — và đây
    là hàng thật rời khỏi kho thật.
    """
    so = _so()
    _cong(so, "1500000")
    so.grant(_qua(so, RewardTier.ONE_MILLION))
    with pytest.raises(RewardAlreadyGrantedError):
        so.grant(_qua(so, RewardTier.ONE_MILLION))


def test_pending_chi_con_moc_chua_trao() -> None:
    so = _so()
    _cong(so, "3200000")
    assert so.pending_tiers() == {RewardTier.ONE_MILLION, RewardTier.THREE_MILLION}
    so.grant(_qua(so, RewardTier.ONE_MILLION))
    assert so.pending_tiers() == {RewardTier.THREE_MILLION}
    so.grant(_qua(so, RewardTier.THREE_MILLION))
    assert so.pending_tiers() == frozenset()


def test_trao_qua_roi_moi_huy_don_thi_qua_KHONG_bi_doi_lai() -> None:
    """🔴 Ca ngoài đời: khách đạt mốc, nhận khẩu trang, hôm sau trả hàng.

    Tích luỹ tụt xuống dưới mốc, nhưng quà **đã ở trong tay khách** — sổ phải
    phản ánh sự thật đó, không được tự xoá bản ghi đã trao. Người quản lý nhìn
    thấy chênh lệch này và tự quyết xử lý; phần mềm không được giả vờ là nó
    chưa từng xảy ra.
    """
    so = _so()
    e = _cong(so, "1100000")
    so.grant(_qua(so, RewardTier.ONE_MILLION))
    so.reverse(e.id, at=NOW)

    assert so.accrued == Decimal("0")
    assert so.granted_tiers() == {RewardTier.ONE_MILLION}  # vẫn còn vết
    assert so.pending_tiers() == frozenset()
