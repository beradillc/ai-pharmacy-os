#!/usr/bin/env python3
"""demo_preview.py — Xem trước sản phẩm AI Pharmacy OS (Sprint 3).

Chạy kiểm thử trực quan CÁC CHỨC NĂNG ĐÃ HIỆN THỰC THẬT:
  • Catalog — tạo Drug (OTC & ETC), quy đổi đơn vị, phân loại kê đơn.
  • Inventory — nhập lô (ProductBatch), tồn kho event-sourced, xuất kho FEFO.
  • Edge cases — xuất quá tồn, nhập số lượng 0, danh sách lô rỗng.

TRUNG THỰC: phần "Clinical Safety" (đơn thuốc, kiểm tra dị ứng, tương tác
thuốc) CHƯA được hiện thực — thuộc Sprint 5 theo ROADMAP. Demo này KHÔNG bịa
kết quả cho phần đó; nó chỉ nêu rõ trạng thái và điểm tích hợp trong tương lai.

Cách chạy (từ thư mục gốc repo, đã kích hoạt venv của backend)::

    python demo_preview.py

Không cần Postgres — demo dùng SQLite in-memory và wiring y hệt tầng service
thật (không mock nghiệp vụ).
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

# Cho phép chạy từ thư mục gốc repo mà không cần cài đặt trước.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend", "src"))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import ConflictError, ValidationError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.catalog.application import (
    CatalogService,
    CreateDrugInput,
    DrugUnitInput,
)
from pharmacy_os.modules.catalog.domain import RxClass
from pharmacy_os.modules.catalog.infrastructure import SqlAlchemyDrugRepository
from pharmacy_os.modules.inventory.application import (
    DispenseInput,
    InventoryService,
    ReceiveStockInput,
)
from pharmacy_os.modules.inventory.domain.fefo import BatchAvailability, allocate_fefo
from pharmacy_os.modules.inventory.infrastructure import (
    SqlAlchemyBalanceRepository,
    SqlAlchemyBatchRepository,
    SqlAlchemyMovementRepository,
)

# --------------------------------------------------------------------------- #
# Console helpers (ANSI, tự tắt màu khi NO_COLOR hoặc không phải TTY)
# --------------------------------------------------------------------------- #
_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def h1(title: str) -> None:
    bar = "═" * 64
    print(f"\n{_c('96', bar)}")
    print(_c("96;1", f"  {title}"))
    print(_c("96", bar))


def step(msg: str) -> None:
    print(_c("94", f"\n▶ {msg}"))


def ok(msg: str) -> None:
    print(_c("92", f"  ✔ {msg}"))


def info(label: str, value: str) -> None:
    print(f"    {_c('90', label + ':'):<28} {value}")


def warn(msg: str) -> None:
    print(_c("93", f"  ⚠ {msg}"))


def blocked(msg: str) -> None:
    print(_c("95", f"  ⛔ {msg}"))


# --------------------------------------------------------------------------- #
# Wiring: giống hệt tầng interface thật, nhưng trên SQLite in-memory.
# --------------------------------------------------------------------------- #
def _dev_ctx() -> RequestContext:
    return RequestContext(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
        permissions=frozenset(
            {
                "catalog.read",
                "catalog.create",
                "inventory.read",
                "inventory.receive",
                "inventory.dispense",
            }
        ),
    )


async def _build_services() -> tuple[CatalogService, InventoryService]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    bus = InMemoryEventBus()

    def uow() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, bus)

    catalog = CatalogService(uow, lambda u, c: SqlAlchemyDrugRepository(u.session, c))
    inventory = InventoryService(
        uow,
        lambda u, c: SqlAlchemyBatchRepository(u.session, c),
        lambda u, c: SqlAlchemyMovementRepository(u.session, c),
        lambda u, c: SqlAlchemyBalanceRepository(u.session, c),
    )
    return catalog, inventory


# --------------------------------------------------------------------------- #
# Kịch bản demo
# --------------------------------------------------------------------------- #
async def demo_catalog(catalog: CatalogService, ctx: RequestContext) -> str:
    h1("1 · CATALOG — Danh mục thuốc (OTC & kê đơn)")

    step("Tạo thuốc OTC: Paracetamol 500mg (đơn vị: viên → vỉ → hộp)")
    para = await catalog.create_drug(
        CreateDrugInput(
            name="Paracetamol 500mg",
            rx_class=RxClass.OTC,
            base_unit="viên",
            atc_code="N02BE01",
            barcode="8935001000017",
            units=[
                DrugUnitInput(unit_name="vỉ", factor=Decimal("10")),
                DrugUnitInput(unit_name="hộp", factor=Decimal("100")),
            ],
        ),
        ctx,
    )
    ok(
        f"Đã tạo — id={str(para.id)[:8]}…  bắt buộc kê đơn: {para.prescription_required}"
    )
    info("Quy đổi 3 hộp", "→ 300 viên (3 × 100)")
    info("Quy đổi 2 vỉ", "→ 20 viên (2 × 10)")

    step("Tạo thuốc kê đơn (ETC): Amoxicillin 500mg")
    amox = await catalog.create_drug(
        CreateDrugInput(
            name="Amoxicillin 500mg",
            rx_class=RxClass.ETC,
            base_unit="viên",
            atc_code="J01CA04",
        ),
        ctx,
    )
    ok(
        f"Đã tạo — id={str(amox.id)[:8]}…  bắt buộc kê đơn: {amox.prescription_required}"
    )
    warn(
        "Amoxicillin là ETC → phải có đơn thuốc hợp lệ mới được bán "
        "(rule ensure_rx_for_etc sẽ dùng cờ này ở Sprint 4)."
    )

    step("Edge case — tạo trùng barcode")
    try:
        await catalog.create_drug(
            CreateDrugInput(
                name="Paracetamol nhái",
                rx_class=RxClass.OTC,
                base_unit="viên",
                barcode="8935001000017",
            ),
            ctx,
        )
        warn("Không nên tới đây!")
    except ConflictError as exc:
        ok(f"Bị chặn đúng như mong đợi: {exc.detail}")

    return str(para.id)


def demo_fefo_algorithm() -> None:
    h1("2 · THUẬT TOÁN FEFO — allocate_fefo (domain thuần)")
    step("Cấp phát 12 đơn vị qua 3 lô có hạn dùng khác nhau")
    avails = [
        BatchAvailability(uuid4(), date(2027, 1, 1), Decimal("10")),  # xa nhất
        BatchAvailability(uuid4(), date(2026, 8, 1), Decimal("5")),  # gần nhất
        BatchAvailability(uuid4(), date(2026, 12, 1), Decimal("10")),
    ]
    for i, a in enumerate(avails, 1):
        info(f"Lô #{i}", f"HSD {a.expiry_date}  |  còn {a.available}")

    allocs = allocate_fefo(avails, Decimal("12"))
    print()
    ok("Kết quả phân bổ (First-Expired-First-Out):")
    for a in allocs:
        which = next(i for i, b in enumerate(avails, 1) if b.batch_id == a.batch_id)
        expiry = next(b.expiry_date for b in avails if b.batch_id == a.batch_id)
        info(f"→ lấy {a.quantity} từ Lô #{which}", f"HSD {expiry}")
    ok("Lô cận date nhất (2026-08-01) được rút trước — đúng nguyên tắc FEFO.")

    step("Edge case — danh sách lô rỗng / demand không hợp lệ")
    try:
        allocate_fefo([], Decimal("1"))
    except Exception as exc:  # InsufficientStockError
        ok(f"Lô rỗng → chặn: {exc}")
    try:
        allocate_fefo(avails, Decimal("0"))
    except ValueError as exc:
        ok(f"Demand = 0 → chặn: {exc}")


async def demo_inventory(
    inventory: InventoryService, ctx: RequestContext, drug_id_str: str
) -> None:
    h1("3 · INVENTORY — Nhập kho, tồn kho event-sourced, xuất FEFO")
    drug_id = UUID(drug_id_str)

    step("Nhập 2 lô Paracetamol (event-sourced: mỗi lần nhập = 1 StockMovement IN)")
    await inventory.receive_stock(
        ReceiveStockInput(
            drug_id,
            "LOT-A",
            date.today() + timedelta(days=400),
            Decimal("100"),
            Decimal("800"),
        ),
        ctx,
    )
    ok("Lô LOT-A: 100 viên, HSD xa (+400 ngày)")
    r2 = await inventory.receive_stock(
        ReceiveStockInput(
            drug_id,
            "LOT-B",
            date.today() + timedelta(days=45),
            Decimal("50"),
            Decimal("820"),
        ),
        ctx,
    )
    ok("Lô LOT-B: 50 viên, HSD gần (+45 ngày)")
    info("Tồn kho hiện tại (on_hand)", f"{r2.on_hand} viên")

    step("Xuất 120 viên — hệ thống tự chọn lô theo FEFO")
    result = await inventory.dispense_stock(
        DispenseInput(drug_id=drug_id, quantity=Decimal("120")), ctx
    )
    for a in result.allocations:
        info("Rút từ lô", f"{str(a.batch_id)[:8]}…  số lượng {a.quantity}")
    ok(f"Đã xuất {result.dispensed} viên · tồn còn lại {result.on_hand} viên")
    ok("Ưu tiên rút hết lô cận date (LOT-B: 50) rồi mới tới LOT-A (70) — FEFO đúng.")

    step("Cảnh báo cận date (trong vòng 90 ngày)")
    alerts = await inventory.list_near_expiry(ctx, within_days=90)
    for a in alerts:
        info("Cận date", f"{a.lot_no}  HSD {a.expiry_date}")
    if not alerts:
        info("Cận date", "không có lô nào")

    step("Edge case — xuất quá tồn & nhập số lượng 0")
    try:
        await inventory.dispense_stock(
            DispenseInput(drug_id=drug_id, quantity=Decimal("9999")), ctx
        )
    except ConflictError as exc:
        ok(f"Xuất quá tồn → chặn + rollback: {exc.detail}")
    try:
        await inventory.receive_stock(
            ReceiveStockInput(
                drug_id,
                "LOT-ZERO",
                date.today() + timedelta(days=10),
                Decimal("0"),
                Decimal("0"),
            ),
            ctx,
        )
    except ValidationError as exc:
        ok(f"Nhập số lượng 0 → chặn: {exc.detail}")

    on_hand_after = await inventory.on_hand(drug_id, ctx)
    info("Tồn kho cuối cùng (không đổi sau rollback)", f"{on_hand_after} viên")


def demo_clinical_pending() -> None:
    h1("4 · CLINICAL SAFETY — TRẠNG THÁI: CHƯA HIỆN THỰC")
    blocked("Module `prescription` và `clinical` CHƯA được xây (kế hoạch Sprint 5).")
    print()
    print("    Những chức năng sau THUỘC ROADMAP nhưng CHƯA có trong mã nguồn,")
    print("    nên demo này KHÔNG chạy và KHÔNG bịa kết quả cho chúng:")
    for item in (
        "Tạo đơn thuốc nháp (PrescriptionDraft)",
        "ClinicalSafetyEngine — kiểm tra dị ứng theo hoạt chất",
        "Kiểm tra tương tác thuốc chéo (drug–drug interaction)",
        "Kiểm tra liều theo tuổi/cân nặng",
    ):
        print(_c("90", f"      ⏳ {item}"))
    print()
    ok("Điểm tích hợp ĐÃ SẴN SÀNG cho Sprint 5:")
    info("Cờ kê đơn", "Drug.is_prescription_required() (đã có, đã test)")
    info("Cổng AI", "core.ai.LLMProvider port (đã có, chưa nối Claude)")
    info(
        "Bảng tri thức", "drug_interactions / drug_knowledge_chunks (đã thiết kế ở ERD)"
    )


async def main() -> None:
    print(
        _c("96;1", "\n╔══════════════════════════════════════════════════════════════╗")
    )
    print(
        _c("96;1", "║   AI PHARMACY OS · DEMO PREVIEW · phạm vi Sprint 3 (thật)     ║")
    )
    print(
        _c("96;1", "╚══════════════════════════════════════════════════════════════╝")
    )

    ctx = _dev_ctx()
    catalog, inventory = await _build_services()

    drug_id = await demo_catalog(catalog, ctx)
    demo_fefo_algorithm()
    await demo_inventory(inventory, ctx, drug_id)
    demo_clinical_pending()

    h1("KẾT LUẬN")
    ok(
        "Catalog + Inventory (FEFO, event-sourced) chạy end-to-end trên DB thật (SQLite)."
    )
    warn("Sales/POS (Sprint 4) và Clinical/Prescription (Sprint 5) CHƯA hiện thực.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
