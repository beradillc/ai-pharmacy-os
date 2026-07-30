"""Adapter cấp phán quyết dị ứng cho `sales` (composition root).

Canh đúng một thứ: adapter **nối lại ba mảnh đã có sẵn cho ra `AllergyRisk` đúng** —
không viết luật khớp mới (kỷ luật #16). Phép khớp thật là của `clinical`, đã có test
riêng; ở đây `clinical` là hàng giả trả về cái mình bảo nó trả.

Chỗ dễ sai nhất và là lý do file này tồn tại: **phân biệt "chưa đồng ý" với "không có
dị ứng"**. `crm.allergy_severities_for_safety_check` trả `{}` cho cả hai, nên nếu
adapter chỉ nhìn kết quả đó thì quầy sẽ được báo "đã kiểm, sạch" trong khi thật ra
phép kiểm chưa từng chạy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

import pytest

from pharmacy_os.api.v1.cross_module import CrmClinicalAllergyRiskProvider
from pharmacy_os.core.errors import NotFoundError

TENANT = uuid4()
KHACH = uuid4()
THUOC = uuid4()
HOAT_CHAT_A = UUID("00000000-0000-0000-0000-0000000000a1")
HOAT_CHAT_B = UUID("00000000-0000-0000-0000-0000000000b2")


@dataclass
class _Khach:
    health_data_allowed: bool


@dataclass
class _HoatChat:
    ingredient_id: UUID
    name: str


@dataclass
class _CanhBao:
    ingredient_id: UUID
    ingredient_name: str
    severity: str


@dataclass
class _KetQua:
    alerts: list[_CanhBao]


class _CrmGia:
    def __init__(
        self, *, dong_y: bool = True, di_ung: dict[UUID, str] | None = None, co_khach: bool = True
    ) -> None:
        self._dong_y, self._di_ung, self._co_khach = dong_y, di_ung or {}, co_khach
        self.so_lan_doc_di_ung = 0

    async def get_customer(self, customer_id: UUID, ctx: Any) -> _Khach:
        if not self._co_khach:
            raise NotFoundError("không có khách")
        return _Khach(health_data_allowed=self._dong_y)

    async def allergy_severities_for_safety_check(
        self, customer_id: UUID, ctx: Any
    ) -> dict[UUID, str]:
        self.so_lan_doc_di_ung += 1
        return dict(self._di_ung)


class _CatalogGia:
    def __init__(self, hoat_chat: list[_HoatChat] | None = None, *, co_thuoc: bool = True) -> None:
        self._hoat_chat, self._co_thuoc = hoat_chat or [], co_thuoc

    async def get_drug_ingredients(self, drug_id: UUID, ctx: Any) -> list[_HoatChat]:
        if not self._co_thuoc:
            raise NotFoundError("thuốc không có trong danh mục")
        return list(self._hoat_chat)


class _ClinicalGia:
    def __init__(self, canh_bao: list[_CanhBao] | None = None) -> None:
        self._canh_bao = canh_bao or []
        self.gio_nhan_duoc: list[UUID] = []

    async def check_allergies(self, data: Any, ctx: Any) -> _KetQua:
        self.gio_nhan_duoc = [b.ingredient_id for b in data.basket]
        return _KetQua(alerts=list(self._canh_bao))


def _provider(catalog: Any, crm: Any, clinical: Any) -> CrmClinicalAllergyRiskProvider:
    return CrmClinicalAllergyRiskProvider(catalog, crm, clinical)


@pytest.mark.asyncio
async def test_khach_khong_ton_tai_tra_None() -> None:
    """`None` ≠ `AllergyRisk(...)` — đơn ghi một khách không còn hồ sơ."""
    p = _provider(_CatalogGia(), _CrmGia(co_khach=False), _ClinicalGia())
    assert await p.for_sale(frozenset({THUOC}), KHACH, TENANT) is None


@pytest.mark.asyncio
async def test_chua_dong_y_thi_bao_KHONG_CHAY_chu_khong_bao_sach() -> None:
    """🔴 Lý do chính file test này tồn tại.

    Chưa đồng ý ⇒ `consent_granted=False`, và **không được gọi** đường đọc dị ứng —
    không có căn cứ pháp lý để xử lý dữ liệu đó (Luật 91/2025 Điều 9).
    """
    crm = _CrmGia(dong_y=False, di_ung={HOAT_CHAT_A: "SEVERE"})
    p = _provider(_CatalogGia(), crm, _ClinicalGia())
    risk = await p.for_sale(frozenset({THUOC}), KHACH, TENANT)
    assert risk is not None
    assert risk.consent_granted is False
    assert risk.conflict_count == 0
    assert crm.so_lan_doc_di_ung == 0  # không đọc dữ liệu sức khoẻ khi chưa được phép


@pytest.mark.asyncio
async def test_dong_y_nhung_khong_khai_di_ung_thi_la_DA_KIEM_VA_SACH() -> None:
    p = _provider(_CatalogGia(), _CrmGia(dong_y=True, di_ung={}), _ClinicalGia())
    risk = await p.for_sale(frozenset({THUOC}), KHACH, TENANT)
    assert risk is not None
    assert risk.consent_granted is True
    assert risk.conflict_count == 0


@pytest.mark.asyncio
async def test_thuoc_khong_co_trong_danh_muc_thi_bo_qua_khong_no() -> None:
    crm = _CrmGia(di_ung={HOAT_CHAT_A: "SEVERE"})
    p = _provider(_CatalogGia(co_thuoc=False), crm, _ClinicalGia())
    risk = await p.for_sale(frozenset({THUOC}), KHACH, TENANT)
    assert risk is not None
    assert risk.consent_granted is True
    assert risk.conflict_count == 0


@pytest.mark.asyncio
async def test_co_xung_dot_thi_dem_dung_so_luong() -> None:
    crm = _CrmGia(di_ung={HOAT_CHAT_A: "MILD", HOAT_CHAT_B: "MODERATE"})
    catalog = _CatalogGia(
        [_HoatChat(HOAT_CHAT_A, "Paracetamol"), _HoatChat(HOAT_CHAT_B, "Ibuprofen")]
    )
    clinical = _ClinicalGia(
        [
            _CanhBao(HOAT_CHAT_A, "Paracetamol", "MILD"),
            _CanhBao(HOAT_CHAT_B, "Ibuprofen", "MODERATE"),
        ]
    )
    risk = await _provider(catalog, crm, clinical).for_sale(frozenset({THUOC}), KHACH, TENANT)
    assert risk is not None
    assert risk.conflict_count == 2


@pytest.mark.asyncio
async def test_chon_dung_muc_do_NANG_NHAT() -> None:
    """Nhiều xung đột thì quầy cần biết cái nặng nhất, không phải cái đầu danh sách."""
    crm = _CrmGia(di_ung={HOAT_CHAT_A: "MILD", HOAT_CHAT_B: "SEVERE"})
    catalog = _CatalogGia([_HoatChat(HOAT_CHAT_A, "A"), _HoatChat(HOAT_CHAT_B, "B")])
    clinical = _ClinicalGia(
        [
            _CanhBao(HOAT_CHAT_A, "A", "MILD"),  # nhẹ đứng TRƯỚC
            _CanhBao(HOAT_CHAT_B, "B", "SEVERE"),
        ]
    )
    risk = await _provider(catalog, crm, clinical).for_sale(frozenset({THUOC}), KHACH, TENANT)
    assert risk is not None
    assert risk.worst_severity == "SEVERE"


@pytest.mark.asyncio
async def test_muc_do_la_van_tinh_la_xung_dot() -> None:
    """crm thêm mức độ mới thì không được rơi mất — vẫn đếm, chỉ không giành "nặng nhất"."""
    crm = _CrmGia(di_ung={HOAT_CHAT_A: "ANAPHYLACTIC", HOAT_CHAT_B: "MILD"})
    catalog = _CatalogGia([_HoatChat(HOAT_CHAT_A, "A"), _HoatChat(HOAT_CHAT_B, "B")])
    clinical = _ClinicalGia(
        [
            _CanhBao(HOAT_CHAT_A, "A", "ANAPHYLACTIC"),
            _CanhBao(HOAT_CHAT_B, "B", "MILD"),
        ]
    )
    risk = await _provider(catalog, crm, clinical).for_sale(frozenset({THUOC}), KHACH, TENANT)
    assert risk is not None
    assert risk.conflict_count == 2
    assert risk.worst_severity == "MILD"  # mức đã biết thắng mức lạ (hạng 0)


@pytest.mark.asyncio
async def test_gio_hang_khu_trung_hoat_chat_lap() -> None:
    """Hai thuốc cùng chứa một hoạt chất chỉ gửi sang clinical MỘT lần."""
    crm = _CrmGia(di_ung={HOAT_CHAT_A: "MILD"})
    catalog = _CatalogGia([_HoatChat(HOAT_CHAT_A, "A")])  # mọi thuốc đều trả cùng hoạt chất
    clinical = _ClinicalGia()
    thuoc2 = uuid4()
    await _provider(catalog, crm, clinical).for_sale(frozenset({THUOC, thuoc2}), KHACH, TENANT)
    assert clinical.gio_nhan_duoc == [HOAT_CHAT_A]
