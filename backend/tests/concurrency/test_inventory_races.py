"""Tái hiện B-01 / B-02 / B-04 — bản vá F-5 đang đóng dần các dấu ``xfail`` ở đây.

> ⚠️ ``xfail(strict=True)`` ở file này nghĩa là **BUG ĐÃ BIẾT, CHƯA VÁ** — KHÔNG
> phải "test đã xanh". Đọc `README.md` cùng thư mục trước khi diễn giải kết quả.
>
> **Trạng thái sau F-5 bước 2/3:** B-01 (2 test) và B-04 (3 test) đã vá, dấu
> ``xfail`` đã gỡ — chúng nay là test xanh thật, canh giữ bản vá. **B-02 (2 test)
> vẫn ĐỎ có chủ đích**, chờ unique index ở bước 3/3.

Thứ tự bắt buộc do kiểm toán đặt ra (F-4 → F-5): **viết test đua trước, vá khoá
hàng sau**. Vá trước rồi mới viết test thì bản vá được nghiệm thu bằng chính bộ
test không thể nhìn thấy lỗi.

Dấu ở đây luôn là ``xfail(strict=True, raises=AssertionError)`` — **cả hai tham số
đều bắt buộc**, đừng bỏ bớt khi thêm test mới:

- ``strict=True``: khi F-5 vá xong, test **chuyển từ xfail sang XPASS và bộ test
  ĐỎ**, buộc người vá quay lại gỡ dấu. Đó là cách duy nhất bản vá được *chứng
  minh* thay vì được *tin*.
- ``raises=AssertionError``: chỉ **khẳng định nghiệp vụ** mới được tính là "đỏ
  đúng dự đoán". Không có nó, tắt Postgres đi là 7 test này báo ``xfailed`` y hệt
  lúc chạy thật — hạ tầng hỏng đội lốt bug-đã-biết, đúng dạng "niềm tin giả" mà
  cả đợt kiểm toán đang sửa (đo thật 2026-07-27: trước khi thêm, tắt Postgres cho
  ra "7 xfailed, 3 errors"; sau khi thêm, 7 test đó thành lỗi thật).

Interleaving ở đây **tất định**, không có ``sleep``: :class:`StatementGate` chặn
đúng câu lệnh ghi đầu tiên của mỗi quầy, nên "cả hai đã đọc xong" là một sự kiện
quan sát được, không phải một hy vọng về thời gian.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import ConflictError
from pharmacy_os.modules.inventory.application import (
    DispenseInput,
    InventoryService,
    ReceiveStockInput,
    SaleDispenseItem,
)
from pharmacy_os.modules.inventory.domain.events import StockShortfallDetected
from pharmacy_os.modules.inventory.infrastructure import SqlAlchemyBalanceRepository
from tests.concurrency.conftest import RecordingBus, StatementGate, both_arrived, finish

BUG_B02 = "B-02: exists_for_ref là check-then-act, không có unique index đỡ"

_UPDATE_BALANCE = "UPDATE stock_balances"
_INSERT_MOVEMENT = "INSERT INTO stock_movements"


# ---------------------------------------------------------------------------
# Tiện ích dựng nền + đọc kết quả
# ---------------------------------------------------------------------------
async def _receive(seeder: InventoryService, ctx: RequestContext, qty: str) -> tuple[UUID, UUID]:
    """Nhập *qty* đơn vị của một thuốc mới qua đúng đường nghiệp vụ. Trả (drug_id, batch_id)."""
    drug_id = uuid4()
    receipt = await seeder.receive_stock(
        ReceiveStockInput(
            drug_id=drug_id,
            lot_no=f"LOT-{drug_id.hex[:8]}",
            expiry_date=date.today() + timedelta(days=365),
            quantity=Decimal(qty),
            cost_price=Decimal("10.00"),
        ),
        ctx,
    )
    return drug_id, receipt.batch_id


async def _balance(observer: AsyncSession, batch_id: UUID) -> Decimal:
    """Số dư sổ kho (bảng chiếu ``stock_balances``)."""
    return (
        await observer.execute(
            text("SELECT quantity FROM stock_balances WHERE batch_id = :b"), {"b": batch_id}
        )
    ).scalar_one()


async def _movement_total(observer: AsyncSession, batch_id: UUID) -> Decimal:
    """Tồn tính từ sổ chi tiết (``stock_movements``) — nguồn sự thật thật sự."""
    return (
        await observer.execute(
            text(
                "SELECT COALESCE(SUM(CASE WHEN type = 'IN' THEN quantity ELSE -quantity END), 0)"
                " FROM stock_movements WHERE batch_id = :b"
            ),
            {"b": batch_id},
        )
    ).scalar_one()


async def _out_rows_for_ref(observer: AsyncSession, ref_id: UUID) -> int:
    return (
        await observer.execute(
            text("SELECT count(*) FROM stock_movements WHERE ref_id = :r"), {"r": ref_id}
        )
    ).scalar_one()


# ---------------------------------------------------------------------------
# B-01 — mất cập nhật ở tầng kho (repository)
# ---------------------------------------------------------------------------
async def test_two_concurrent_adjusts_must_both_land(
    seeder: InventoryService,
    ctx: RequestContext,
    session_a: AsyncSession,
    session_b: AsyncSession,
    observer: AsyncSession,
    engine_a: object,
    engine_b: object,
) -> None:
    """Nhập 100, hai quầy cùng trừ 10 ⇒ phải còn 80.

    ``adjust`` đọc số dư rồi ghi lại ``đã_đọc + delta`` mà **không khoá hàng**. Hai
    giao dịch cùng đọc 100, cùng ghi 90: một lần trừ **biến mất không dấu vết**.
    Đây là dạng thuần tuý nhất của B-01, ở đúng tầng gây lỗi.
    """
    drug_id, batch_id = await _receive(seeder, ctx, "100")

    gate_a = StatementGate(engine_a, _UPDATE_BALANCE)  # type: ignore[arg-type]
    gate_b = StatementGate(engine_b, _UPDATE_BALANCE)  # type: ignore[arg-type]

    async def party(session: AsyncSession) -> None:
        repo = SqlAlchemyBalanceRepository(session, ctx)
        await repo.adjust(drug_id, batch_id, ctx.branch_id, ctx.tenant_id, Decimal("-10"))
        await session.commit()

    task_a = asyncio.create_task(party(session_a))
    task_b = asyncio.create_task(party(session_b))

    await both_arrived(gate_a, gate_b)  # cả hai ĐÃ ĐỌC 100, chưa ai ghi
    gate_a.open()
    await finish(task_a)  # A ghi + commit
    gate_b.open()
    await finish(task_b)  # B ghi + commit trên số đã đọc cũ

    assert await _balance(observer, batch_id) == Decimal("80.000")


async def test_ledger_and_balance_must_agree_after_concurrent_dispense(
    seeder: InventoryService,
    ctx: RequestContext,
    service_a: InventoryService,
    service_b: InventoryService,
    observer: AsyncSession,
    engine_a: object,
    engine_b: object,
) -> None:
    """Sổ chi tiết và sổ tổng phải khớp nhau — đây là "sổ kho tự mâu thuẫn" của kiểm toán.

    Hai quầy cùng xuất 10 trên tồn 100. Mỗi bên ghi đủ dòng OUT của mình (sổ chi
    tiết đúng: còn 80) nhưng bảng chiếu ``stock_balances`` chỉ nhận một lần trừ
    (còn 90). Người bán nhìn số dư, kiểm kê nhìn sổ chi tiết, hai bên **không bao
    giờ khớp** và không ai biết bên nào sai.
    """
    drug_id, batch_id = await _receive(seeder, ctx, "100")

    gate_a = StatementGate(engine_a, _UPDATE_BALANCE)  # type: ignore[arg-type]
    gate_b = StatementGate(engine_b, _UPDATE_BALANCE)  # type: ignore[arg-type]

    async def party(service: InventoryService) -> None:
        await service.dispense_stock(DispenseInput(drug_id=drug_id, quantity=Decimal("10")), ctx)

    task_a = asyncio.create_task(party(service_a))
    task_b = asyncio.create_task(party(service_b))

    await both_arrived(gate_a, gate_b)
    gate_a.open()
    await finish(task_a)
    gate_b.open()
    await finish(task_b)

    assert await _balance(observer, batch_id) == await _movement_total(observer, batch_id)


# ---------------------------------------------------------------------------
# B-02 — giao trùng một đơn hàng
# ---------------------------------------------------------------------------
@pytest.mark.xfail(strict=True, raises=AssertionError, reason=BUG_B02)
async def test_same_sale_dispatched_twice_writes_one_set_of_movements(
    seeder: InventoryService,
    ctx: RequestContext,
    service_a: InventoryService,
    service_b: InventoryService,
    observer: AsyncSession,
    engine_a: object,
    engine_b: object,
) -> None:
    """Một đơn hàng giao 2 lần (relay at-least-once) phải chỉ trừ kho MỘT lần.

    ``dispense_for_sale`` chống trùng bằng ``exists_for_ref`` — đọc xong rồi mới
    ghi, không khoá gì ở giữa. Hai bản giao cùng lúc đều thấy "chưa có" nên đều
    trừ kho: đúng cảnh kiểm toán tái hiện được (nhập 10, xuất 16).
    """
    drug_id, batch_id = await _receive(seeder, ctx, "100")
    order_id = uuid4()

    gate_a = StatementGate(engine_a, _INSERT_MOVEMENT)  # type: ignore[arg-type]
    gate_b = StatementGate(engine_b, _INSERT_MOVEMENT)  # type: ignore[arg-type]

    items = [SaleDispenseItem(drug_id=drug_id, quantity=Decimal("5"))]

    async def party(service: InventoryService) -> None:
        await service.dispense_for_sale(items, order_id, ctx)

    task_a = asyncio.create_task(party(service_a))
    task_b = asyncio.create_task(party(service_b))

    await both_arrived(gate_a, gate_b)  # cả hai đã kiểm "đã giao chưa" và đều thấy CHƯA
    gate_a.open()
    await finish(task_a)
    gate_b.open()
    await finish(task_b)

    assert await _out_rows_for_ref(observer, order_id) == 1
    assert await _movement_total(observer, batch_id) == Decimal("95.000")


@pytest.mark.xfail(strict=True, raises=AssertionError, reason=BUG_B02)
async def test_database_rejects_two_movements_for_same_ref_and_batch(
    seeder: InventoryService, ctx: RequestContext, observer: AsyncSession
) -> None:
    """Chống trùng phải có **ràng buộc CSDL** đỡ, không chỉ một câu ``SELECT`` trong code.

    Ràng buộc đúng là duy nhất trên ``(tenant_id, ref_type, ref_id, batch_id)``,
    **không phải** trên ``(tenant_id, ref_type, ref_id)``: một lần xuất FEFO trải
    trên nhiều lô ghi nhiều dòng cùng ``ref_id`` một cách hợp lệ. Ghi rõ ở đây vì
    F-5 sẽ đặt index này — đặt sai phạm vi là chặn nhầm nghiệp vụ đúng.
    """
    _, batch_id = await _receive(seeder, ctx, "100")
    ref_id = uuid4()
    insert = text(
        "INSERT INTO stock_movements"
        " (id, tenant_id, branch_id, drug_id, batch_id, type, quantity, ref_type, ref_id,"
        "  occurred_at, created_at, updated_at)"
        " VALUES (:id, :tenant_id, :branch_id, :drug_id, :batch_id, 'OUT', 5, 'sale', :ref_id,"
        "  now(), now(), now())"
    )
    params = {
        "tenant_id": ctx.tenant_id,
        "branch_id": ctx.branch_id,
        "drug_id": uuid4(),
        "batch_id": batch_id,
        "ref_id": ref_id,
    }

    await observer.execute(insert, {**params, "id": uuid4()})
    rejected = False
    try:
        await observer.execute(insert, {**params, "id": uuid4()})
        await observer.flush()
    except IntegrityError:
        rejected = True

    # Cố ý KHÔNG dùng `pytest.raises`: nó ném `Failed`, không phải `AssertionError`,
    # nên sẽ lọt qua `raises=AssertionError` của dấu xfail — đúng cái lỗ vừa bịt.
    assert rejected, "CSDL nhận 2 dòng xuất kho cho cùng (ref_id, batch_id) — thiếu unique index"


# ---------------------------------------------------------------------------
# B-04 — bán vượt tồn
# ---------------------------------------------------------------------------
async def test_concurrent_dispense_never_exceeds_stock_on_hand(
    seeder: InventoryService,
    ctx: RequestContext,
    service_a: InventoryService,
    service_b: InventoryService,
    observer: AsyncSession,
    engine_a: object,
    engine_b: object,
) -> None:
    """Tồn 10, hai quầy cùng xuất 6 ⇒ tổng xuất KHÔNG được quá 10.

    Đây là bất biến nghiệp vụ, không phải chi tiết kỹ thuật: nhà thuốc không thể
    giao 12 viên khi trong kho có 10. Hiện cả hai cùng đọc "còn 10", cùng cho phép,
    và hàng thiếu 2 viên chỉ lộ ra khi kiểm kê.
    """
    drug_id, batch_id = await _receive(seeder, ctx, "10")

    gate_a = StatementGate(engine_a, _INSERT_MOVEMENT)  # type: ignore[arg-type]
    gate_b = StatementGate(engine_b, _INSERT_MOVEMENT)  # type: ignore[arg-type]

    async def party(service: InventoryService) -> None:
        # Bên thua cuộc BỊ TỪ CHỐI là kết quả MONG MUỐN sau khi F-5 vá xong —
        # nuốt ConflictError ở đây để khẳng định cuối cùng nói về TỒN KHO, không
        # phải về việc bên nào thắng cuộc đua.
        with suppress(ConflictError):
            await service.dispense_stock(DispenseInput(drug_id=drug_id, quantity=Decimal("6")), ctx)

    task_a = asyncio.create_task(party(service_a))
    task_b = asyncio.create_task(party(service_b))

    await both_arrived(gate_a, gate_b)
    gate_a.open()
    await finish(task_a)
    gate_b.open()
    await finish(task_b)

    dispensed = (
        await observer.execute(
            text(
                "SELECT COALESCE(SUM(quantity), 0) FROM stock_movements"
                " WHERE batch_id = :b AND type = 'OUT'"
            ),
            {"b": batch_id},
        )
    ).scalar_one()
    assert dispensed <= Decimal("10.000"), f"đã xuất {dispensed} trên tồn 10"


async def test_concurrent_dispense_never_drives_balance_negative(
    seeder: InventoryService,
    ctx: RequestContext,
    service_a: InventoryService,
    service_b: InventoryService,
    observer: AsyncSession,
    engine_a: object,
    engine_b: object,
) -> None:
    """Số dư một lô **không bao giờ** được âm — sổ kho âm là sổ kho không dùng được.

    Tách khỏi test trên có chủ đích: "xuất quá tồn" và "số dư âm" là hai triệu
    chứng khác nhau của cùng một lỗ hổng, và bản vá F-5 phải đóng cả hai. Vá được
    một cái rồi báo xong là kiểu overclaim mà kỷ luật #6 cấm.
    """
    drug_id, batch_id = await _receive(seeder, ctx, "10")

    gate_a = StatementGate(engine_a, _INSERT_MOVEMENT)  # type: ignore[arg-type]
    gate_b = StatementGate(engine_b, _INSERT_MOVEMENT)  # type: ignore[arg-type]

    async def party(service: InventoryService) -> None:
        with suppress(ConflictError):
            await service.dispense_stock(DispenseInput(drug_id=drug_id, quantity=Decimal("6")), ctx)

    task_a = asyncio.create_task(party(service_a))
    task_b = asyncio.create_task(party(service_b))

    await both_arrived(gate_a, gate_b)
    gate_a.open()
    await finish(task_a)
    gate_b.open()
    await finish(task_b)

    assert await _movement_total(observer, batch_id) >= Decimal("0")


async def test_concurrent_sale_shortfall_leaves_a_trail(
    seeder: InventoryService,
    ctx: RequestContext,
    service_a: InventoryService,
    service_b: InventoryService,
    bus_a: RecordingBus,
    bus_b: RecordingBus,
    engine_a: object,
    engine_b: object,
) -> None:
    """Thiếu hàng do đua phải phát ``StockShortfallDetected`` — không được im lặng.

    ``dispense_for_sale`` **cố ý** không chặn đơn (đơn đã chốt rồi) mà phát sự kiện
    thiếu hàng để người vận hành lần ra. Nhưng cả hai bên đều đọc "còn đủ 10" nên
    **không bên nào** thấy mình thiếu: hàng hụt 2 viên và không có một dòng nào
    trong hệ thống nói rằng điều đó đã xảy ra. Đây là phần *"không dòng đối soát"*
    của B-04 — nặng hơn con số sai, vì con số sai còn có thể phát hiện khi kiểm kê.
    """
    drug_id, _ = await _receive(seeder, ctx, "10")

    gate_a = StatementGate(engine_a, _INSERT_MOVEMENT)  # type: ignore[arg-type]
    gate_b = StatementGate(engine_b, _INSERT_MOVEMENT)  # type: ignore[arg-type]

    async def party(service: InventoryService, order_id: UUID) -> None:
        await service.dispense_for_sale(
            [SaleDispenseItem(drug_id=drug_id, quantity=Decimal("6"))], order_id, ctx
        )

    task_a = asyncio.create_task(party(service_a, uuid4()))
    task_b = asyncio.create_task(party(service_b, uuid4()))

    await both_arrived(gate_a, gate_b)
    gate_a.open()
    await finish(task_a)
    gate_b.open()
    await finish(task_b)

    shortfalls = bus_a.of_type(StockShortfallDetected) + bus_b.of_type(StockShortfallDetected)
    assert shortfalls, "hàng hụt 2 viên mà không sự kiện nào ghi nhận"
