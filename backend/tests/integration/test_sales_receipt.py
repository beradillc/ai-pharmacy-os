"""``SalesService.get_receipt`` — printable projection for In bill (S7)."""

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import NotFoundError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
    SalesService,
)
from pharmacy_os.modules.sales.domain import DrugInfo, PaymentMethod
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository


class FakeDrugDisplay:
    def __init__(self, display_by_drug: dict[UUID, tuple[str, str]]) -> None:
        self._display = display_by_drug

    async def get(self, drug_id: UUID, tenant_id: UUID) -> DrugInfo | None:
        if drug_id not in self._display:
            return None
        name, unit = self._display[drug_id]
        return DrugInfo(drug_id=drug_id, requires_prescription=False, name=name, unit=unit)


class FakeNguoiBan:
    """Cổng tra tên người bán, dựng sẵn theo `user_id`. `None` = không tra được."""

    def __init__(self, ten_theo_id: dict[UUID, str | None]) -> None:
        self._ten = ten_theo_id

    async def name_of(self, user_id: UUID, tenant_id: UUID) -> str | None:
        return self._ten.get(user_id)


def _service(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    provider: FakeDrugDisplay | None,
    nguoi_ban: FakeNguoiBan | None = None,
) -> SalesService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
        provider,
        salesperson_info=nguoi_ban,
    )


async def test_get_receipt_resolves_display_and_computes_change(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    drug = uuid4()
    display = FakeDrugDisplay({drug: ("Paracetamol 500mg", "viên")})
    svc = _service(session_factory, event_bus, display)
    sale = await svc.complete_sale(
        CreateSaleInput(
            client_uuid="receipt-1",
            lines=[SaleLineInput(drug_id=drug, quantity=Decimal("2"), unit_price=Decimal("10000"))],
            # Cash tender exceeds the 20000 subtotal — customer gets 5000 back.
            payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("25000"))],
        ),
        ctx,
    )

    receipt = await svc.get_receipt(sale.id, ctx)

    assert receipt.order_id == sale.id
    assert receipt.subtotal == Decimal("20000")
    assert receipt.paid_total == Decimal("25000")
    assert receipt.change_amount == Decimal("5000")
    assert len(receipt.lines) == 1
    line = receipt.lines[0]
    assert line.name == "Paracetamol 500mg"
    assert line.unit == "viên"
    assert line.line_total == Decimal("20000")
    assert len(receipt.payments) == 1
    assert receipt.payments[0].method == PaymentMethod.CASH


async def test_get_receipt_unknown_drug_falls_back_to_id(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    drug = uuid4()
    svc = _service(session_factory, event_bus, FakeDrugDisplay({}))
    # 🔴 `require_known_drugs=False` — KHÔNG phải để né cổng mới, mà vì đây chính là trạng
    # thái duy nhất còn dựng được: từ 2026-07-31 một đơn MỚI không thể mang thuốc lạ nữa
    # (phương án B). Hoá đơn của một thuốc đã bị gỡ khỏi danh mục vẫn phải in được — đơn ấy
    # tới qua `/sync/sales`, và tính chất mà test này canh không hề đổi.
    sale = await svc.complete_sale(
        CreateSaleInput(
            client_uuid="receipt-2",
            lines=[SaleLineInput(drug_id=drug, quantity=Decimal("1"), unit_price=Decimal("5000"))],
            payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("5000"))],
        ),
        ctx,
        require_known_drugs=False,
    )

    receipt = await svc.get_receipt(sale.id, ctx)

    assert receipt.change_amount == Decimal("0")
    assert receipt.lines[0].name == str(drug)
    assert receipt.lines[0].unit == ""


async def test_get_receipt_no_drug_info_provider_falls_back_to_id(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    drug = uuid4()
    svc = _service(session_factory, event_bus, None)
    sale = await svc.complete_sale(
        CreateSaleInput(
            client_uuid="receipt-3",
            lines=[SaleLineInput(drug_id=drug, quantity=Decimal("1"), unit_price=Decimal("5000"))],
            payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("5000"))],
        ),
        ctx,
    )

    receipt = await svc.get_receipt(sale.id, ctx)

    assert receipt.lines[0].name == str(drug)


async def test_get_receipt_unknown_order_raises_not_found(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    svc = _service(session_factory, event_bus, None)
    with pytest.raises(NotFoundError):
        await svc.get_receipt(uuid4(), ctx)


async def test_receipt_mang_ten_nguoi_ban(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Chain giao 2026-08-01: hoá đơn in ra phải có người bán."""
    drug = uuid4()
    svc = _service(
        session_factory,
        event_bus,
        FakeDrugDisplay({drug: ("Paracetamol 500mg", "viên")}),
        FakeNguoiBan({ctx.user_id: "Trịnh Thư"}),
    )
    sale = await svc.complete_sale(
        CreateSaleInput(
            client_uuid="receipt-nguoi-ban",
            lines=[SaleLineInput(drug_id=drug, quantity=Decimal("1"), unit_price=Decimal("10000"))],
            payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("10000"))],
        ),
        ctx,
    )

    receipt = await svc.get_receipt(sale.id, ctx)

    assert receipt.sold_by_name == "Trịnh Thư"


async def test_receipt_khong_tra_duoc_ten_thi_bo_han_dong(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
    ctx: RequestContext,
) -> None:
    """Không tra được ⇒ `None`, KHÔNG phải chuỗi rỗng hay mã UUID cụt.

    Ba nhánh cùng về `None` và cùng một hệ quả — hoá đơn bỏ hẳn dòng đó: cổng chưa nối,
    người bán đã bị xoá, đơn cũ hơn cột `sold_by_user_id`. Test này canh nhánh "đã xoá";
    nhánh "chưa nối" là mọi test khác trong tệp (dựng `SalesService` không có cổng).
    """
    drug = uuid4()
    svc = _service(
        session_factory,
        event_bus,
        FakeDrugDisplay({drug: ("Paracetamol 500mg", "viên")}),
        FakeNguoiBan({}),  # iam không còn người này
    )
    sale = await svc.complete_sale(
        CreateSaleInput(
            client_uuid="receipt-khong-ten",
            lines=[SaleLineInput(drug_id=drug, quantity=Decimal("1"), unit_price=Decimal("10000"))],
            payments=[PaymentInput(method=PaymentMethod.CASH, amount=Decimal("10000"))],
        ),
        ctx,
    )

    receipt = await svc.get_receipt(sale.id, ctx)

    assert receipt.sold_by_name is None
