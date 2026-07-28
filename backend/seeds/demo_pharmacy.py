"""Dựng một nhà thuốc DEMO đầy đủ dữ liệu để đưa khách hàng xem (Sprint 10, D4).

Vì sao cần: mọi màn hình đã chạy được từ trước, nhưng trên một cơ sở dữ liệu
trống thì màn nào cũng là một khung rỗng. Thứ khách hàng đánh giá trong 10 phút
là *nhà thuốc của họ trông như thế nào trong phần mềm này*, nên demo cần danh
mục thuốc thật, tồn kho có lô và hạn dùng lệch nhau, và một đường doanh thu có
lên có xuống.

Cách chạy (từ ``backend/``, venv đã kích hoạt, CSDL đã migrate)::

    DEMO_ADMIN_PASSWORD='NhaThuocDemo2026' python -m seeds.demo_pharmacy \\
        --tenant-name "Nhà thuốc Bera Demo" \\
        --branch-code HQ --branch-name "Cơ sở 1 — Quận 1" \\
        --admin-email demo@bera.vn --admin-full-name "Dược sĩ Trần Minh"

Chạy lại với cùng ``--admin-email`` sẽ **dừng có báo lỗi**, không ghi đè: một
lệnh seed âm thầm sửa dữ liệu đang có là đúng loại rủi ro mà kỷ luật #7 nói tới.
Muốn dựng lại thì đổi email/tenant, hoặc xoá tenant cũ bằng tay.

🔴 **BA CHỖ DỮ LIỆU DEMO KHÔNG PHẢN ÁNH ĐÚNG ĐỜI THẬT — đọc trước khi tin màn
hình, và đừng dùng CSDL này để đo hiệu năng hay đối chiếu nghiệp vụ:**

1. **Đơn bán được lùi ngày bằng một câu UPDATE thẳng vào cột ``created_at``.**
   Đường doanh thu 28 ngày chỉ tồn tại được nhờ chỗ này: ``created_at`` do CSDL
   đặt (``server_default now()``) và tầng dịch vụ không nhận ngày từ ngoài, đúng
   như nó nên thế. Lệnh lùi ngày **chỉ** chạm ``sales_orders.created_at``.
2. **Bút toán kho mang ngày HÔM NAY.** Hàng có bị trừ thật (mỗi đơn demo đều gọi
   ``dispense_stock``, FEFO thật, tồn cuối là tồn thật), nhưng *thời điểm* trừ
   thì không lùi theo đơn. Nghĩa là: tồn kho hiện tại đúng, lịch sử di chuyển kho
   thì không.
3. **Chỉ bán thuốc OTC.** Không có đơn thuốc nào được tạo, nên bán ETC ở đây sẽ
   là một demo dạy sai luật. Thuốc ETC vẫn nằm trong danh mục và trong kho để
   màn Tồn kho có đủ hình dạng.

Dữ liệu ngẫu nhiên nhưng **cố định**: ``random.Random(20260728)``. Hai lần chạy
cho ra cùng một nhà thuốc, nên ảnh chụp màn hình trong tài liệu bán hàng không
lệch với thứ khách hàng thấy khi bấm thử.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import text

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import get_settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.errors import AppError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.catalog.application import (
    CatalogService,
    CreateDrugInput,
    DrugUnitInput,
)
from pharmacy_os.modules.catalog.domain import RxClass
from pharmacy_os.modules.catalog.infrastructure import (
    SqlAlchemyActiveIngredientRepository,
    SqlAlchemyDrugRepository,
)
from pharmacy_os.modules.crm.application import CreateCustomerInput, CrmService
from pharmacy_os.modules.crm.infrastructure import SqlAlchemyCustomerRepository
from pharmacy_os.modules.iam.application import BootstrapTenantInput, IamService
from pharmacy_os.modules.iam.interface import build_repositories
from pharmacy_os.modules.inventory.application import (
    DispenseInput,
    InventoryService,
    ReceiveStockInput,
)
from pharmacy_os.modules.inventory.infrastructure import (
    SqlAlchemyBalanceRepository,
    SqlAlchemyBatchRepository,
    SqlAlchemyMovementRepository,
    SqlAlchemyStockReconciliationRepository,
)
from pharmacy_os.modules.procurement.application import (
    CreatePurchaseOrderInput,
    CreateSupplierInput,
    ProcurementService,
    PurchaseOrderItemInput,
)
from pharmacy_os.modules.procurement.infrastructure import (
    SqlAlchemyGoodsReceiptRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemySupplierRepository,
)
from pharmacy_os.modules.sales.application import (
    CreateSaleInput,
    PaymentInput,
    SaleLineInput,
    SalesService,
)
from pharmacy_os.modules.sales.domain import PaymentMethod
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository

_log = structlog.get_logger("demo")

_PASSWORD_ENV = "DEMO_ADMIN_PASSWORD"

#: Ngẫu nhiên CÓ HẠT CỐ ĐỊNH — xem docstring module.
_RNG = random.Random(20260728)

#: Quyền của phiên seed. Không đọc từ vai trò trong CSDL: script này chạy bằng
#: thông tin đăng nhập CSDL, nên nó vốn đã mạnh hơn mọi vai; giả vờ đi qua RBAC
#: chỉ tạo cảm giác an toàn chứ không thêm an toàn.
_SEED_PERMISSIONS = frozenset(
    {
        "catalog.create",
        "catalog.read",
        "inventory.receive",
        "inventory.read",
        "inventory.dispense",
        "sales.create",
        "sales.read",
        "crm.create",
        "crm.read",
        "procurement.supplier.create",
        "procurement.supplier.read",
        "procurement.po.create",
        "procurement.po.read",
        "procurement.po.write",
    }
)

#: (tên, nhóm kê đơn, dạng, hàm lượng, đơn vị lẻ, giá bán lẻ VND, mức bán/ngày)
#: Giá là giá bán lẻ tham khảo, làm tròn — dữ liệu demo, không phải bảng giá.
_DRUGS: list[tuple[str, RxClass, str, str, str, int, int]] = [
    ("Paracetamol 500mg", RxClass.OTC, "Viên nén", "500mg", "viên", 1200, 40),
    ("Efferalgan 500mg", RxClass.OTC, "Viên sủi", "500mg", "viên", 4500, 12),
    ("Panadol Extra", RxClass.OTC, "Viên nén", "500mg+65mg", "viên", 2500, 18),
    ("Ibuprofen 400mg", RxClass.OTC, "Viên nén", "400mg", "viên", 1500, 14),
    ("Alaxan", RxClass.OTC, "Viên nén", "325mg+200mg", "viên", 2200, 10),
    ("Vitamin C 500mg", RxClass.OTC, "Viên nén", "500mg", "viên", 800, 30),
    ("Vitamin 3B", RxClass.OTC, "Viên nang", "—", "viên", 1500, 12),
    ("Berberin 100mg", RxClass.OTC, "Viên nén", "100mg", "viên", 500, 16),
    ("Smecta", RxClass.OTC, "Bột pha", "3g", "gói", 5500, 14),
    ("Oresol", RxClass.OTC, "Bột pha", "—", "gói", 4000, 9),
    ("Loratadin 10mg", RxClass.OTC, "Viên nén", "10mg", "viên", 1000, 11),
    ("Cetirizin 10mg", RxClass.OTC, "Viên nén", "10mg", "viên", 900, 10),
    ("Dextromethorphan 15mg", RxClass.OTC, "Viên nén", "15mg", "viên", 1300, 8),
    ("Bổ phế Nam Hà", RxClass.OTC, "Siro", "125ml", "chai", 28000, 5),
    ("Prospan", RxClass.OTC, "Siro", "100ml", "chai", 95000, 3),
    ("Domperidon 10mg", RxClass.OTC, "Viên nén", "10mg", "viên", 900, 9),
    ("Omeprazol 20mg", RxClass.OTC, "Viên nang", "20mg", "viên", 1800, 12),
    ("Phosphalugel", RxClass.OTC, "Gel uống", "20g", "gói", 6500, 10),
    ("Men vi sinh Enterogermina", RxClass.OTC, "Ống uống", "5ml", "ống", 9000, 8),
    ("Natri clorid 0,9% nhỏ mắt", RxClass.OTC, "Dung dịch", "10ml", "lọ", 6000, 7),
    ("Povidon iod 10%", RxClass.OTC, "Dung dịch", "20ml", "lọ", 12000, 4),
    ("Băng gạc y tế", RxClass.OTC, "Vật tư", "—", "gói", 8000, 6),
    ("Khẩu trang y tế 4 lớp", RxClass.OTC, "Vật tư", "—", "hộp", 35000, 5),
    ("Nhiệt kế điện tử", RxClass.OTC, "Thiết bị", "—", "cái", 120000, 1),
    ("Canxi D3", RxClass.OTC, "Viên nang", "—", "viên", 2500, 9),
    ("Dầu gió xanh", RxClass.OTC, "Dung dịch", "12ml", "lọ", 18000, 4),
    # ETC — có trong danh mục và trong kho, KHÔNG bán trong dữ liệu demo.
    ("Amoxicillin 500mg", RxClass.ETC, "Viên nang", "500mg", "viên", 2000, 0),
    ("Augmentin 625mg", RxClass.ETC, "Viên nén", "500mg+125mg", "viên", 12000, 0),
    ("Cefixim 200mg", RxClass.ETC, "Viên nang", "200mg", "viên", 6500, 0),
    ("Azithromycin 500mg", RxClass.ETC, "Viên nén", "500mg", "viên", 9000, 0),
    ("Metformin 500mg", RxClass.ETC, "Viên nén", "500mg", "viên", 1100, 0),
    ("Amlodipin 5mg", RxClass.ETC, "Viên nén", "5mg", "viên", 1000, 0),
    ("Losartan 50mg", RxClass.ETC, "Viên nén", "50mg", "viên", 2400, 0),
    ("Atorvastatin 20mg", RxClass.ETC, "Viên nén", "20mg", "viên", 3200, 0),
    ("Prednisolon 5mg", RxClass.ETC, "Viên nén", "5mg", "viên", 700, 0),
    ("Salbutamol xịt", RxClass.ETC, "Bình xịt", "100mcg", "bình", 78000, 0),
]

_SUPPLIERS: list[tuple[str, str, str]] = [
    ("Công ty CP Dược Hậu Giang", "1800581888", "kinhdoanh@dhgpharma.com.vn"),
    ("Công ty CP Traphaco", "02435334594", "traphaco@traphaco.com.vn"),
    ("Công ty CP Dược phẩm Imexpharm", "02773853106", "info@imexpharm.com"),
    ("Công ty TNHH Zuellig Pharma Việt Nam", "02838260000", "vn.info@zuelligpharma.com"),
]

_CUSTOMERS: list[tuple[str, str, str]] = [
    ("Nguyễn Thị Hồng", "0903111222", "F"),
    ("Trần Văn Bình", "0912333444", "M"),
    ("Lê Thị Mai", "0987555666", "F"),
    ("Phạm Quốc Hùng", "0938777888", "M"),
    ("Võ Thị Kim Chi", "0906999000", "F"),
    ("Đặng Minh Tuấn", "0977123456", "M"),
    ("Bùi Thị Lan", "0918234567", "F"),
    ("Hoàng Văn Nam", "0965345678", "M"),
    ("Ngô Thị Thu Hà", "0949456789", "F"),
    ("Đỗ Trọng Nghĩa", "0932567890", "M"),
]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dựng nhà thuốc demo có dữ liệu đầy đủ.")
    parser.add_argument("--tenant-name", default="Nhà thuốc Bera Demo")
    parser.add_argument("--branch-code", default="HQ")
    parser.add_argument("--branch-name", default="Cơ sở 1 — Quận 1")
    parser.add_argument("--admin-email", default="demo@bera.vn")
    parser.add_argument("--admin-full-name", default="Dược sĩ Trần Minh")
    parser.add_argument(
        "--days", type=int, default=28, help="Số ngày lịch sử bán hàng (mặc định 28)"
    )
    return parser.parse_args(argv)


class _Services:
    """Mọi service dựng trên cùng một session factory, giống composition root."""

    def __init__(self, session_factory: object, event_bus: InMemoryEventBus) -> None:
        self._session_factory = session_factory

        def uow_factory() -> UnitOfWork:
            return SqlAlchemyUnitOfWork(session_factory, event_bus)  # type: ignore[arg-type]

        audit = AuditLogger(session_factory)  # type: ignore[arg-type]
        self.iam = IamService(uow_factory, build_repositories, audit)
        self.catalog = CatalogService(
            uow_factory,
            lambda uow, c: SqlAlchemyDrugRepository(uow.session, c),
            lambda uow: SqlAlchemyActiveIngredientRepository(uow.session),
            audit,
        )
        self.inventory = InventoryService(
            uow_factory,
            lambda uow, c: SqlAlchemyBatchRepository(uow.session, c),
            lambda uow, c: SqlAlchemyMovementRepository(uow.session, c),
            lambda uow, c: SqlAlchemyBalanceRepository(uow.session, c),
            lambda uow, c: SqlAlchemyStockReconciliationRepository(uow.session, c),
            audit,
        )
        self.sales = SalesService(
            uow_factory,
            lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
            audit=audit,
        )
        self.crm = CrmService(
            uow_factory,
            lambda uow, c: SqlAlchemyCustomerRepository(uow.session, c),
            audit,
        )
        self.procurement = ProcurementService(
            uow_factory,
            lambda uow, c: SqlAlchemySupplierRepository(uow.session, c),
            lambda uow, c: SqlAlchemyPurchaseOrderRepository(uow.session, c),
            lambda uow, c: SqlAlchemyGoodsReceiptRepository(uow.session, c),
            audit,
        )


_PACK_UNIT = "hộp"


def _pack_units(base_unit: str) -> list[DrugUnitInput]:
    """Đơn vị đóng gói cho một thuốc bán theo ``base_unit``.

    Rỗng khi đơn vị lẻ ĐÃ LÀ "hộp": catalog từ chối hai đơn vị trùng tên trên
    cùng một thuốc, và nó từ chối đúng. Lần chạy seed đầu tiên đổ ở đây, sau 22
    thuốc đã ghi — nên quy tắc này tách ra thành hàm để có chỗ mà kiểm, thay vì
    nằm lẫn trong một vòng lặp chỉ chạy được khi có CSDL thật.
    """
    if base_unit == _PACK_UNIT:
        return []
    return [DrugUnitInput(unit_name=_PACK_UNIT, factor=Decimal("10"))]


async def _seed_catalog(svc: _Services, ctx: RequestContext) -> dict[str, tuple[UUID, int, int]]:
    """Tạo danh mục thuốc. Trả về ``tên -> (id, giá bán, mức bán/ngày)``."""
    created: dict[str, tuple[UUID, int, int]] = {}
    for index, (name, rx, form, strength, unit, price, velocity) in enumerate(_DRUGS):
        out = await svc.catalog.create_drug(
            CreateDrugInput(
                name=name,
                rx_class=rx,
                base_unit=unit,
                form=form,
                strength=strength,
                # Mã vạch giả nhưng đúng hình dạng EAN-13 tiền tố Việt Nam (893).
                barcode=f"893{5000000000 + index:010d}",
                units=_pack_units(unit),
            ),
            ctx,
        )
        created[name] = (out.id, price, velocity)
    return created


async def _seed_stock(
    svc: _Services, ctx: RequestContext, drugs: dict[str, tuple[UUID, int, int]], days: int
) -> int:
    """Nhập kho: mỗi thuốc 2 lô, vài thuốc có một lô CẬN HẠN để màn cảnh báo có việc.

    Lượng nhập = đủ bán ``days`` ngày × 3, tối thiểu 60 — để lịch sử bán chạy hết
    mà kho không cạn (cạn giữa chừng thì đường doanh thu tự nhiên cụt, và đó là
    một cái sai trông y hệt một cái đúng).
    """
    lots = 0
    for position, (name, (drug_id, _price, velocity)) in enumerate(drugs.items()):
        quantity = max(60, velocity * days * 3)
        far = date.today() + timedelta(days=_RNG.randint(400, 900))
        # Cứ 6 thuốc thì 1 có lô cận hạn (15–75 ngày).
        near = date.today() + timedelta(days=_RNG.randint(15, 75) if position % 6 == 0 else 200)
        for lot_index, (expiry, qty) in enumerate(
            ((near, quantity // 3), (far, quantity - quantity // 3))
        ):
            if qty <= 0:
                continue
            await svc.inventory.receive_stock(
                ReceiveStockInput(
                    drug_id=drug_id,
                    lot_no=f"{name[:3].upper()}{position:02d}{lot_index}-2026",
                    expiry_date=expiry,
                    quantity=Decimal(qty),
                    cost_price=Decimal(_price_cost(_price)),
                ),
                ctx,
            )
            lots += 1
    return lots


def _price_cost(retail_price: int) -> int:
    """Giá vốn ≈ 72% giá bán lẻ — một biên gộp nhà thuốc nhìn vào thấy quen."""
    return int(retail_price * 0.72)


async def _seed_customers(svc: _Services, ctx: RequestContext) -> list[UUID]:
    ids: list[UUID] = []
    for full_name, phone, gender in _CUSTOMERS:
        out = await svc.crm.create_customer(
            CreateCustomerInput(full_name=full_name, phone=phone, gender=gender), ctx
        )
        ids.append(out.id)
    return ids


async def _seed_suppliers_and_orders(
    svc: _Services, ctx: RequestContext, drugs: dict[str, tuple[UUID, int, int]]
) -> tuple[int, int]:
    supplier_ids: list[UUID] = []
    for name, phone, email in _SUPPLIERS:
        out = await svc.procurement.create_supplier(
            CreateSupplierInput(name=name, phone=phone, email=email), ctx
        )
        supplier_ids.append(out.id)

    names = list(drugs)
    orders = 0
    for index, supplier_id in enumerate(supplier_ids[:3]):
        picked = _RNG.sample(names, 4)
        po = await svc.procurement.create_purchase_order(
            CreatePurchaseOrderInput(
                supplier_id=supplier_id,
                items=[
                    PurchaseOrderItemInput(
                        drug_id=drugs[n][0],
                        quantity_ordered=Decimal(_RNG.choice([100, 200, 500])),
                        unit_price=Decimal(_price_cost(drugs[n][1])),
                    )
                    for n in picked
                ],
            ),
            ctx,
        )
        orders += 1
        # Đơn đầu để nháp (màn "đơn mua nháp chờ duyệt" có việc), còn lại đã gửi NCC.
        if index > 0:
            await svc.procurement.mark_ordered(po.id, ctx)
    return len(supplier_ids), orders


async def _seed_sales(
    svc: _Services,
    ctx: RequestContext,
    drugs: dict[str, tuple[UUID, int, int]],
    customers: list[UUID],
    days: int,
) -> list[tuple[UUID, datetime]]:
    """Sinh lịch sử bán. Trả về ``(order_id, thời điểm muốn lùi về)``.

    Cuối tuần đông hơn ngày thường (hệ số 1,35) và mỗi ngày dao động ±25 %: một
    đường doanh thu phẳng lì trông giả ngay từ cái nhìn đầu tiên.
    """
    sellable = [(name, *value) for name, value in drugs.items() if value[2] > 0]
    backdate: list[tuple[UUID, datetime]] = []
    today = date.today()

    for day_offset in range(days - 1, -1, -1):
        day = today - timedelta(days=day_offset)
        weekend = day.weekday() >= 5
        orders_today = int(_RNG.randint(6, 12) * (1.35 if weekend else 1.0))
        for order_index in range(orders_today):
            picked = _RNG.sample(sellable, _RNG.randint(1, 4))
            lines: list[SaleLineInput] = []
            total = Decimal("0")
            for _name, drug_id, price, _velocity in picked:
                qty = Decimal(_RNG.randint(1, 6))
                lines.append(
                    SaleLineInput(
                        drug_id=drug_id,
                        quantity=qty,
                        unit_price=Decimal(price),
                        requires_prescription=False,
                    )
                )
                total += qty * Decimal(price)

            # Khoảng 1/3 đơn gắn với khách quen — số còn lại là khách vãng lai,
            # đúng như một nhà thuốc thật, và cũng là thứ làm màn Khách hàng có
            # nghĩa thay vì chỉ là một danh bạ.
            customer_id = _RNG.choice(customers) if _RNG.random() < 0.34 else None
            method = _RNG.choices(
                [PaymentMethod.CASH, PaymentMethod.TRANSFER, PaymentMethod.CARD],
                weights=[70, 22, 8],
            )[0]
            try:
                out = await svc.sales.complete_sale(
                    CreateSaleInput(
                        client_uuid=f"demo-{day.isoformat()}-{order_index}",
                        lines=lines,
                        payments=[PaymentInput(method=method, amount=total)],
                        customer_id=customer_id,
                    ),
                    ctx,
                )
            except AppError as exc:  # kho cạn hoặc dữ liệu lệch — bỏ đơn, không dừng
                _log.warning("demo_sale_skipped", day=day.isoformat(), reason=exc.detail)
                continue

            # Trừ kho thật (FEFO). Bút toán mang ngày hôm nay — giới hạn đã ghi ở
            # docstring module, mục 2.
            for line in lines:
                try:
                    await svc.inventory.dispense_stock(
                        DispenseInput(
                            drug_id=line.drug_id,
                            quantity=line.quantity,
                            ref_type="sale",
                            ref_id=out.id,
                        ),
                        ctx,
                    )
                except AppError as exc:
                    _log.warning("demo_dispense_skipped", reason=exc.detail)

            hour = _RNG.randint(7, 20)
            minute = _RNG.randint(0, 59)
            backdate.append((out.id, datetime.combine(day, time(hour, minute), tzinfo=UTC)))
    return backdate


async def _backdate_orders(session_factory: object, rows: list[tuple[UUID, datetime]]) -> None:
    """Lùi ngày đơn bán — xem cảnh báo số 1 ở docstring module.

    Một câu ``UPDATE`` cho mỗi đơn, chạy trong một giao dịch. Không đụng bất kỳ
    cột nào khác, không đụng bảng nào khác.
    """
    async with session_factory() as session:  # type: ignore[operator]
        for order_id, moment in rows:
            await session.execute(
                text("UPDATE sales_orders SET created_at = :moment WHERE id = :id"),
                {"moment": moment, "id": str(order_id)},
            )
        await session.commit()


async def _clear_must_change_password(session_factory: object, email: str) -> None:
    """Tắt cờ đổi mật khẩu lần đầu cho TÀI KHOẢN DEMO.

    Cố ý và chỉ ở đây: buộc đổi mật khẩu là hành vi đúng cho một triển khai thật
    (``bootstrap_tenant`` giữ nguyên), nhưng một buổi demo mà câu đầu tiên là
    "mời anh đặt mật khẩu mới" thì hỏng mất mười giây đầu.
    """
    async with session_factory() as session:  # type: ignore[operator]
        await session.execute(
            text("UPDATE users SET must_change_password = false WHERE email = :email"),
            {"email": email},
        )
        await session.commit()


async def _run(args: argparse.Namespace, password: str) -> None:
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    session_factory = build_sessionmaker(engine)
    svc = _Services(session_factory, InMemoryEventBus())

    try:
        tenant = await svc.iam.bootstrap_tenant(
            BootstrapTenantInput(
                tenant_name=args.tenant_name,
                branch_code=args.branch_code,
                branch_name=args.branch_name,
                admin_email=args.admin_email,
                admin_full_name=args.admin_full_name,
                admin_password=password,
            )
        )
        ctx = RequestContext(
            tenant_id=tenant.tenant_id,
            branch_id=tenant.branch_id,
            user_id=tenant.admin_user_id,
            permissions=_SEED_PERMISSIONS,
        )

        drugs = await _seed_catalog(svc, ctx)
        lots = await _seed_stock(svc, ctx, drugs, args.days)
        customers = await _seed_customers(svc, ctx)
        suppliers, orders = await _seed_suppliers_and_orders(svc, ctx, drugs)
        sales = await _seed_sales(svc, ctx, drugs, customers, args.days)
        await _backdate_orders(session_factory, sales)
        await _clear_must_change_password(session_factory, args.admin_email)
    finally:
        await engine.dispose()

    _log.info(
        "demo_seed_complete",
        tenant_id=str(tenant.tenant_id),
        branch_id=str(tenant.branch_id),
        drugs=len(drugs),
        lots=lots,
        customers=len(customers),
        suppliers=suppliers,
        purchase_orders=orders,
        sales=len(sales),
        days=args.days,
    )
    print(  # noqa: T201 - tóm tắt cho người chạy, không phải log ứng dụng
        f"\n✅ Nhà thuốc demo đã sẵn sàng — {args.tenant_name}\n"
        f"   {len(drugs)} thuốc · {lots} lô · {len(customers)} khách · "
        f"{suppliers} NCC · {orders} đơn mua · {len(sales)} hoá đơn / {args.days} ngày\n\n"
        f"   Đăng nhập: {args.admin_email} / (mật khẩu vừa đặt)\n"
        f"   Giao diện: http://localhost:3000/login\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    password = os.environ.get(_PASSWORD_ENV)
    if not password:
        print(  # noqa: T201
            f"Thiếu {_PASSWORD_ENV}. Ví dụ:\n"
            f"  {_PASSWORD_ENV}='NhaThuocDemo2026' python -m seeds.demo_pharmacy",
            file=sys.stderr,
        )
        return 2
    try:
        asyncio.run(_run(args, password))
    except AppError as exc:
        # Email đã tồn tại là trường hợp thường gặp nhất: chạy lại lần hai.
        print(f"Lỗi: {exc.detail}", file=sys.stderr)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
