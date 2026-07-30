"""Cột "Điểm đã tích trong năm" + đồng ý BASIC ghi tại quầy (Chain chốt 2026-07-31).

Hai thứ đi cùng nhau vì cùng phục vụ một câu của Chain: *"lưu số đt là mặc định khi có
được số điện thoại"*. Điều đáng canh nhất **không phải** là đồng ý có được ghi hay không,
mà là **nó KHÔNG lan sang hai mục đích kia** — đó chính là lỗi "lấy đồng ý cho việc A rồi
dùng cho việc B", và nó trông rất hợp lý lúc làm vì đằng nào cũng chỉ là một số điện thoại.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.crm.application import CreateCustomerInput, CrmService
from pharmacy_os.modules.crm.domain import ConsentBasis, ConsentPurpose


class _DocGia:
    """Cổng đọc điểm giả — phép cộng thật là của `sales`, đã có test riêng."""

    def __init__(self, diem: dict[UUID, Decimal] | None = None) -> None:
        self._diem = diem or {}
        self.duoc_hoi: list[list[UUID]] = []

    async def accrued_this_year(
        self, customer_ids: list[UUID], tenant_id: UUID
    ) -> dict[UUID, Decimal]:
        self.duoc_hoi.append(list(customer_ids))
        return dict(self._diem)


# --- đồng ý tại quầy ----------------------------------------------------------


async def test_co_so_dien_thoai_thi_GHI_dong_y_BASIC_co_so_COUNTER(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    out = await crm_service.create_customer(
        CreateCustomerInput(full_name="Có số", phone="0900111222"), ctx
    )
    basic = [c for c in out.consents if c.purpose == ConsentPurpose.BASIC]
    assert len(basic) == 1
    assert basic[0].granted is True
    # COUNTER, không phải EXPLICIT: không ai đọc điều khoản cho khách nghe ở bước này.
    assert basic[0].basis == ConsentBasis.COUNTER


async def test_KHONG_lan_sang_LOYALTY_va_HEALTH(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """🔴 Phép kiểm quan trọng nhất cả file.

    Đưa số để ghi lên hoá đơn **không phải** đồng ý cho theo dõi lịch sử mua, càng không
    phải đồng ý lưu dị ứng/bệnh nền (Luật 91/2025 Điều 9 — đồng ý theo từng mục đích).
    `ConsentBasis.COUNTER` ghi rõ nó *chỉ thoả cho BASIC*; test này giữ cho câu đó đúng.
    """
    out = await crm_service.create_customer(
        CreateCustomerInput(full_name="Có số", phone="0900111333"), ctx
    )
    co = {c.purpose for c in out.consents if c.granted}
    assert co == {ConsentPurpose.BASIC}
    assert out.health_data_allowed is False


async def test_KHONG_co_so_dien_thoai_thi_KHONG_ghi_dong_y_nao(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """Không có hành vi khẳng định nào xảy ra ⇒ không có gì để ghi. Ghi bừa ở đây là
    đúng nghĩa "coi im lặng là đồng ý"."""
    out = await crm_service.create_customer(CreateCustomerInput(full_name="Không số"), ctx)
    assert out.consents == []
    assert out.health_data_allowed is False


async def test_so_rong_khong_tinh_la_co_so(crm_service: CrmService, ctx: RequestContext) -> None:
    out = await crm_service.create_customer(CreateCustomerInput(full_name="Số rỗng", phone=""), ctx)
    assert out.consents == []


# --- điểm tích trong năm ------------------------------------------------------


async def test_danh_sach_khach_mang_theo_diem(crm_service: CrmService, ctx: RequestContext) -> None:
    a = await crm_service.create_customer(CreateCustomerInput(full_name="A"), ctx)
    doc = _DocGia({a.id: Decimal("3450000")})
    crm_service.attach_accrual_reader(doc)
    ds = await crm_service.list_customers(ctx)
    assert next(c for c in ds if c.id == a.id).accrued_this_year == Decimal("3450000")


async def test_hoi_MOT_luot_cho_ca_trang_khong_phai_moi_dong_mot_luot(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """🔴 Điều dễ làm sai nhất khi thêm một cột: N+1. Một trang 50 khách mà hỏi 50 lượt
    thì cột này tự nó làm chậm màn chính."""
    for i in range(3):
        await crm_service.create_customer(CreateCustomerInput(full_name=f"K{i}"), ctx)
    doc = _DocGia()
    crm_service.attach_accrual_reader(doc)
    await crm_service.list_customers(ctx)
    assert len(doc.duoc_hoi) == 1
    assert len(doc.duoc_hoi[0]) == 3


async def test_chua_noi_cong_doc_thi_diem_bang_0_chu_khong_no(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    """Cột điểm là tính năng PHỤ — thiếu nó màn Khách hàng vẫn phải chạy."""
    await crm_service.create_customer(CreateCustomerInput(full_name="Chưa nối"), ctx)
    ds = await crm_service.list_customers(ctx)
    assert all(c.accrued_this_year == Decimal(0) for c in ds)


async def test_khach_chua_mua_gi_thi_0_khong_phai_vang_mat(
    crm_service: CrmService, ctx: RequestContext
) -> None:
    a = await crm_service.create_customer(CreateCustomerInput(full_name="A"), ctx)
    b = await crm_service.create_customer(CreateCustomerInput(full_name="B"), ctx)
    crm_service.attach_accrual_reader(_DocGia({a.id: Decimal("100000")}))
    ds = {c.id: c.accrued_this_year for c in await crm_service.list_customers(ctx)}
    assert ds[a.id] == Decimal("100000")
    assert ds[b.id] == Decimal(0)


@pytest.mark.parametrize(
    ("tich", "so_hop"),
    [
        (Decimal("0"), 0),
        (Decimal("1999999"), 0),
        (Decimal("2000000"), 1),
        (Decimal("4500000"), 2),
    ],
)
async def test_diem_khop_voi_luat_tich_diem(tich: Decimal, so_hop: int) -> None:
    """Cột này là **cơ số** của `boxes_earned`, không phải một con số trang trí — nên nó
    phải là đúng thứ luật tích điểm chia cho `REWARD_STEP`."""
    from pharmacy_os.modules.crm.domain.loyalty import boxes_earned

    assert boxes_earned(tich) == so_hop
