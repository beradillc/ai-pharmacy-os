"""Cấp phát mã đơn mua dưới tải đồng thời — B3, khe hở G-2 (docs/19).

**Vì sao mã PO phải có test đua, không chỉ test đơn vị:** mã đơn mua là một chuỗi
tăng dần cấp cho *nhiều người bấm cùng lúc*. Đó đúng là hình dạng lỗi mà kiểm toán
2026-07-26 tìm thấy ở tồn kho (B-01: đọc rồi ghi, hai bên cùng đọc một giá trị) và
F-5 vừa vá. Viết ``SELECT max(...)`` rồi ``+1`` ở đây sẽ **xanh trên mọi test đơn
lẻ** và phát cùng một số cho hai dược sĩ vào đúng ngày nhà thuốc bận nhất.

Bản cài đặt đặt phép cộng **bên trong** ``UPDATE … RETURNING`` nên khoá hàng do
chính câu lệnh giữ. Ba test dưới đây kiểm ba mặt khác nhau của điều đó:

1. hai lượt cấp phát đồng thời khi bộ đếm **đã có** ⇒ hai mã khác nhau;
2. hai lượt cấp phát đồng thời khi bộ đếm **chưa có** (đua ở nhánh INSERT);
3. ràng buộc duy nhất ``(tenant_id, code)`` thật sự chặn ở tầng CSDL — lưới đỡ
   cuối, phòng khi có đường ghi nào sau này không đi qua ``next_code``.

Test 3 tồn tại vì bài học F-5: khoá đúng ở tầng ứng dụng vẫn cần ràng buộc ở tầng
CSDL, bởi tầng ứng dụng chỉ bảo vệ được những đường đi mà nó biết.
"""

from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.modules.procurement.infrastructure import SqlAlchemyPurchaseOrderRepository
from tests.concurrency.conftest import StatementGate, both_arrived, finish


def _ctx(tenant_id: UUID) -> RequestContext:
    return RequestContext(
        tenant_id=tenant_id,
        branch_id=uuid4(),
        user_id=uuid4(),
        permissions=frozenset({"procurement.po.create"}),
    )


async def _allocate(factory: async_sessionmaker[AsyncSession], tenant_id: UUID) -> str:
    """Cấp một mã trong giao dịch riêng, rồi commit — đúng như đường thật làm."""
    async with factory() as session:
        repo = SqlAlchemyPurchaseOrderRepository(session, _ctx(tenant_id))
        code = await repo.next_code()
        await session.commit()
        return code


async def _last_value(observer: AsyncSession, tenant_id: UUID) -> int:
    return (
        await observer.execute(
            text("SELECT last_value FROM purchase_order_counters WHERE tenant_id = :t"),
            {"t": tenant_id},
        )
    ).scalar_one()


async def test_concurrent_allocation_never_repeats_a_code(
    engine_a: AsyncEngine,
    engine_b: AsyncEngine,
    factory_a: async_sessionmaker[AsyncSession],
    factory_b: async_sessionmaker[AsyncSession],
    observer: AsyncSession,
) -> None:
    """Hai quầy cấp mã cùng lúc trên bộ đếm ĐÃ có ⇒ hai số khác nhau.

    🔴 **Test này BẮT BUỘC phải dùng ``StatementGate``, đừng gỡ ra.** Bản đầu của
    nó chỉ ``asyncio.gather`` hai lượt cấp phát rồi khẳng định hai mã khác nhau —
    và **xanh cả với bản cài đặt sai** (``SELECT`` rồi ``UPDATE``), đã đo thật:
    ``gather`` không ép xen kẽ, quầy A chạy trọn rồi B mới đọc, nên B đọc được giá
    trị A đã ghi. Một test đua không ép được xen kẽ chỉ đang khẳng định *"chạy tuần
    tự thì ra đúng"*.

    Cổng chặn **câu lệnh đầu tiên** của mỗi quầy (tiền tố rỗng ⇒ khớp mọi câu),
    nên nó dựng được điểm "cả hai đã tới trước khi bên nào kịp ghi" **bất kể** cài
    đặt gửi ``UPDATE`` hay ``SELECT`` trước. Nhờ vậy cổng bắt được bản sai thay vì
    bắt được cách viết.
    """
    tenant_id = uuid4()
    async with factory_a() as seed:
        repo = SqlAlchemyPurchaseOrderRepository(seed, _ctx(tenant_id))
        first = await repo.next_code()
        await seed.commit()
    assert first == "PO-0001"

    gate_a = StatementGate(engine_a, "")
    gate_b = StatementGate(engine_b, "")
    codes: dict[str, str] = {}

    async def counter(name: str, factory: async_sessionmaker[AsyncSession]) -> None:
        codes[name] = await _allocate(factory, tenant_id)

    task_a = asyncio.create_task(counter("a", factory_a))
    task_b = asyncio.create_task(counter("b", factory_b))

    # Cả hai đứng ngay trước câu lệnh đầu tiên — chưa bên nào ghi gì.
    await both_arrived(gate_a, gate_b)
    gate_a.open()
    gate_b.open()
    await finish(task_a, task_b)

    assert codes["a"] != codes["b"], f"hai quầy nhận cùng một mã đơn mua: {codes['a']}"
    assert sorted(codes.values()) == ["PO-0002", "PO-0003"]
    assert await _last_value(observer, tenant_id) == 3


async def test_first_ever_allocation_races_on_the_insert(
    engine_a: AsyncEngine,
    engine_b: AsyncEngine,
    factory_a: async_sessionmaker[AsyncSession],
    factory_b: async_sessionmaker[AsyncSession],
    observer: AsyncSession,
) -> None:
    """Đơn mua ĐẦU TIÊN của một nhà thuốc: bộ đếm chưa tồn tại, hai bên cùng INSERT.

    Nhánh này không có hàng nào để khoá, nên nó dựa vào ràng buộc khoá chính: bên
    thua nhận ``IntegrityError``, rollback **đúng phần chèn đó** (savepoint) rồi quay
    lại nhánh ``UPDATE``. Ca hiếm nhưng xảy ra đúng lúc tệ nhất — ngày khai trương.

    Ghi rõ giới hạn: test này **không** phân biệt được bản cài đặt đúng với bản
    ``SELECT``-rồi-``UPDATE``, vì cả hai đều đi qua nhánh INSERT rồi thử lại. Nó
    canh nhánh thử-lại, không canh khoá hàng — việc đó là của test ở trên.
    """
    tenant_id = uuid4()
    gate_a = StatementGate(engine_a, "")
    gate_b = StatementGate(engine_b, "")
    codes: dict[str, str] = {}

    async def counter(name: str, factory: async_sessionmaker[AsyncSession]) -> None:
        codes[name] = await _allocate(factory, tenant_id)

    task_a = asyncio.create_task(counter("a", factory_a))
    task_b = asyncio.create_task(counter("b", factory_b))

    await both_arrived(gate_a, gate_b)
    gate_a.open()
    gate_b.open()
    await finish(task_a, task_b)

    assert codes["a"] != codes["b"], f"hai quầy nhận cùng một mã ở lần cấp đầu: {codes['a']}"
    assert sorted(codes.values()) == ["PO-0001", "PO-0002"]
    assert await _last_value(observer, tenant_id) == 2


async def test_database_refuses_a_duplicate_code_even_if_the_counter_is_bypassed(
    observer: AsyncSession,
) -> None:
    """Lưới đỡ cuối: ``uq_po_tenant_code`` phải có răng ở tầng CSDL.

    ``next_code`` bảo vệ được những đường ghi đi qua nó. Ràng buộc này bảo vệ cả
    những đường chưa tồn tại — script sửa tay, migration tương lai, hoặc một
    repository mới quên gọi ``next_code``. Bài học F-5: khoá ở ứng dụng và ràng buộc
    ở CSDL không thay thế nhau.
    """
    tenant_id, branch_id, supplier_id = uuid4(), uuid4(), uuid4()
    insert = text(
        "INSERT INTO purchase_orders"
        " (id, tenant_id, branch_id, supplier_id, code, status, created_at, updated_at)"
        " VALUES (:id, :tenant_id, :branch_id, :supplier_id, :code, 'DRAFT', now(), now())"
    )
    params = {
        "tenant_id": tenant_id,
        "branch_id": branch_id,
        "supplier_id": supplier_id,
        "code": "PO-0001",
    }

    await observer.execute(insert, {**params, "id": uuid4()})
    await observer.commit()

    with pytest.raises(IntegrityError):
        await observer.execute(insert, {**params, "id": uuid4()})
        await observer.commit()
    await observer.rollback()


async def test_two_tenants_each_start_at_one(
    factory_a: async_sessionmaker[AsyncSession],
    factory_b: async_sessionmaker[AsyncSession],
) -> None:
    """Bộ đếm theo TENANT, không phải toàn CSDL — lý do không dùng ``SEQUENCE``.

    Hai nhà thuốc khác nhau đều phải có đơn PO-0001 của riêng mình; nhà thuốc thứ
    hai mở phần mềm mà thấy đơn đầu tiên của mình là PO-0457 thì con số đó đang nói
    về khách hàng khác.
    """
    tenant_one, tenant_two = uuid4(), uuid4()

    code_one, code_two = await asyncio.gather(
        _allocate(factory_a, tenant_one), _allocate(factory_b, tenant_two)
    )

    assert code_one == "PO-0001"
    assert code_two == "PO-0001"
