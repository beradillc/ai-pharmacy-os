"""Cổng dị ứng ở `complete_sale` — điểm cưỡng chế thật của Đ-6.

Đ-6 (Chain chốt 2026-07-30): **cảnh báo + buộc xác nhận có ghi vết**, không chặn cứng.
Đ-7 nói cảnh báo hiện lúc thêm thuốc vào đơn, nhưng **cưỡng chế đặt ở lúc hoàn tất** —
giỏ có thể đổi sau lần POS kiểm, và một client hoàn toàn có thể bỏ qua lượt kiểm ấy.

Chạy thẳng ``SalesService.complete_sale`` với một ``AllergyRiskProvider`` giả; adapter
thật (``CrmClinicalAllergyRiskProvider``) đã có test riêng ở
``tests/unit/test_allergy_risk_provider.py``.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import ValidationError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.application.dto import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
)
from pharmacy_os.modules.sales.domain import AllergyRisk, PaymentMethod
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository

LY_DO = "Bác sĩ đã chỉ định, khách dùng nhiều lần không sao"


class _CongGia:
    """Trả về một phán quyết cố định, và đếm số lần được hỏi."""

    def __init__(self, risk: AllergyRisk | None) -> None:
        self._risk = risk
        self.calls: list[tuple[frozenset[UUID], UUID, UUID]] = []

    async def for_sale(
        self, drug_ids: frozenset[UUID], customer_id: UUID, tenant_id: UUID
    ) -> AllergyRisk | None:
        self.calls.append((drug_ids, customer_id, tenant_id))
        return self._risk


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    cong: _CongGia | None,
) -> SalesService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
        None,  # drug_info
        None,  # prescription_info
        None,  # audit
        cong,
    )


def _don(client_uuid: str, *, khach: UUID | None, ly_do: str | None = None) -> CreateSaleInput:
    return CreateSaleInput(
        client_uuid=client_uuid,
        lines=[
            SaleLineInput(
                drug_id=uuid4(),
                quantity=Decimal("1"),
                unit_price=Decimal("10000"),
                requires_prescription=False,
            )
        ],
        payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("10000"))],
        customer_id=khach,
        allergy_acknowledgement=ly_do,
    )


async def test_chua_noi_cong_thi_ban_binh_thuong(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """🔴 Phép kiểm hồi quy chính: mọi cài đặt cũ (chưa nối provider) giữ nguyên hành vi."""
    service = _service(session_factory, event_bus, None)
    out = await service.complete_sale(_don("no-port", khach=uuid4()), ctx)
    assert out.status == "COMPLETED"


async def test_don_khong_ghi_khach_thi_khong_hoi_cong(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Bán vãng lai OTC hợp lệ không có khách — không có gì để đối chiếu, và không
    được vì thế mà tốn một lượt gọi sang crm/clinical."""
    cong = _CongGia(AllergyRisk(consent_granted=True, conflict_count=3, worst_severity="SEVERE"))
    service = _service(session_factory, event_bus, cong)
    out = await service.complete_sale(_don("walk-in", khach=None), ctx)
    assert out.status == "COMPLETED"
    assert cong.calls == []


async def test_khong_co_xung_dot_thi_ban_duoc(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    cong = _CongGia(AllergyRisk(consent_granted=True, conflict_count=0))
    service = _service(session_factory, event_bus, cong)
    out = await service.complete_sale(_don("clean", khach=uuid4()), ctx)
    assert out.status == "COMPLETED"
    assert cong.calls  # đã thật sự hỏi qua cổng


async def test_chua_dong_y_du_lieu_suc_khoe_van_ban_duoc(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Đ-10: từ chối bán vì khách chưa đồng ý là phạt khách vì họ thực hiện quyền của
    mình (Luật 91/2025 Điều 9), mà lại không có xung đột nào được biết là tồn tại."""
    cong = _CongGia(AllergyRisk(consent_granted=False))
    service = _service(session_factory, event_bus, cong)
    out = await service.complete_sale(_don("no-consent", khach=uuid4()), ctx)
    assert out.status == "COMPLETED"


async def test_co_xung_dot_ma_khong_ghi_ly_do_thi_BI_CHAN(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    cong = _CongGia(AllergyRisk(consent_granted=True, conflict_count=2, worst_severity="SEVERE"))
    service = _service(session_factory, event_bus, cong)
    with pytest.raises(ValidationError) as err:
        await service.complete_sale(_don("blocked", khach=uuid4()), ctx)
    # Thông điệp phải đọc được ở POS: bao nhiêu cảnh báo, nặng cỡ nào.
    assert "2" in str(err.value)
    assert "SEVERE" in str(err.value)


async def test_don_bi_chan_thi_KHONG_duoc_luu(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Cổng nằm TRƯỚC order.complete() và trước khối ghi CSDL — đơn bị chặn không được
    để lại dấu vết nào, nếu không lần bán lại cùng client_uuid sẽ bị coi là replay."""
    cong = _CongGia(AllergyRisk(consent_granted=True, conflict_count=1, worst_severity="MILD"))
    service = _service(session_factory, event_bus, cong)
    with pytest.raises(ValidationError):
        await service.complete_sale(_don("retry-me", khach=uuid4()), ctx)

    # Lần hai, cùng client_uuid, nay có lý do → phải bán được thật, không phải replay.
    out = await service.complete_sale(_don("retry-me", khach=uuid4(), ly_do=LY_DO), ctx)
    assert out.status == "COMPLETED"


async def test_ghi_ly_do_thi_ban_duoc(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    cong = _CongGia(AllergyRisk(consent_granted=True, conflict_count=1, worst_severity="SEVERE"))
    service = _service(session_factory, event_bus, cong)
    out = await service.complete_sale(_don("acked", khach=uuid4(), ly_do=LY_DO), ctx)
    assert out.status == "COMPLETED"


@pytest.mark.parametrize("trong", ["", "   "])
async def test_ly_do_toan_khoang_trang_khong_tinh(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
    trong: str,
) -> None:
    cong = _CongGia(AllergyRisk(consent_granted=True, conflict_count=1, worst_severity="MILD"))
    service = _service(session_factory, event_bus, cong)
    with pytest.raises(ValidationError):
        await service.complete_sale(_don(f"blank{len(trong)}", khach=uuid4(), ly_do=trong), ctx)


async def test_cong_nhan_dung_gio_hang_va_dung_khach(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Cổng phải được hỏi bằng giỏ hàng THẬT của đơn đang hoàn tất, không phải giỏ nào
    khác — đây là điều làm nó khác một lượt kiểm phía client."""
    khach = uuid4()
    cong = _CongGia(AllergyRisk(consent_granted=True, conflict_count=0))
    service = _service(session_factory, event_bus, cong)
    don = _don("basket", khach=khach)
    await service.complete_sale(don, ctx)
    drug_ids, customer_id, tenant_id = cong.calls[0]
    assert drug_ids == frozenset({line.drug_id for line in don.lines})
    assert customer_id == khach
    assert tenant_id == ctx.tenant_id
