"""`CatalogService.set_drug_price` — đường đổi giá niêm yết, tầng app+infra.

Vì sao cần tầng này ngoài test domain: domain chỉ biết gán một `Decimal` trong bộ nhớ.
Bốn thứ chỉ ở đây mới kiểm được, và ba trong bốn là chỗ đã hỏng thật trong dự án này:

* **giá mới và dòng lịch sử phải cùng vào CSDL trong một lượt** — quên một trong hai thì
  `drugs.sale_price` và `drug_price_history` nói hai chuyện khác nhau, im lặng;
* **cổng này không được ghi đè trường khác** (tên/mã vạch/hoạt chất) — đúng bẫy `to_orm()`
  đã ghi ở `save_ingredients`;
* **`catalog.update` là quyền cấp chuỗi**, thu ngân và dược sĩ chi nhánh không có;
* **đổi giá đã có thì phải ghi lý do**, đặt giá lần đầu thì không.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction
from pharmacy_os.core.audit.models import AuditLogORM
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.catalog.application.dto import CreateDrugInput, DrugOutput
from pharmacy_os.modules.catalog.infrastructure.models import DrugPriceHistoryORM


async def _thuoc(
    svc: CatalogService, ctx: RequestContext, *, gia: Decimal | None = None
) -> DrugOutput:
    return await svc.create_drug(
        CreateDrugInput(
            name=f"Thuốc-{uuid4().hex[:6]}",
            rx_class="OTC",
            base_unit="viên",
            sale_price=gia,
        ),
        ctx,
    )


async def _lich_su(
    session_factory: async_sessionmaker[AsyncSession], drug_id: object
) -> list[DrugPriceHistoryORM]:
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(DrugPriceHistoryORM)
                .where(DrugPriceHistoryORM.drug_id == drug_id)
                .order_by(DrugPriceHistoryORM.changed_at, DrugPriceHistoryORM.id)
            )
        ).scalars()
        return list(rows)


async def test_dat_gia_lan_dau_ghi_ca_gia_LAN_dong_lich_su(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """🔴 Phép kiểm quan trọng nhất của bước này.

    Ghi giá mà quên ghi lịch sử là hỏng **im lặng**: màn hình vẫn đúng, chỉ có câu hỏi
    "ngày ấy niêm yết bao nhiêu" là mất câu trả lời. Đọc thẳng bảng, không qua service.
    """
    thuoc = await _thuoc(catalog_service, ctx)
    assert thuoc.sale_price is None

    out = await catalog_service.set_drug_price(thuoc.id, Decimal("12000"), None, ctx)

    assert out.sale_price == Decimal("12000")
    rows = await _lich_su(session_factory, thuoc.id)
    assert len(rows) == 1
    assert rows[0].old_price is None  # lần ĐẦU đặt giá, không phải đổi giá
    assert rows[0].new_price == Decimal("12000")
    assert rows[0].changed_by == ctx.user_id


async def test_doi_gia_giu_gia_cu_trong_dong_lich_su(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    thuoc = await _thuoc(catalog_service, ctx, gia=Decimal("12000"))
    await catalog_service.set_drug_price(thuoc.id, Decimal("13500"), "NPP tăng giá", ctx)

    rows = await _lich_su(session_factory, thuoc.id)
    assert len(rows) == 1
    assert rows[0].old_price == Decimal("12000")
    assert rows[0].new_price == Decimal("13500")
    assert rows[0].reason == "NPP tăng giá"


async def test_doi_gia_ma_thieu_ly_do_bi_tu_choi_va_KHONG_ghi_gi(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Từ chối rồi vẫn ghi mất nửa vời là tệ hơn không làm gì."""
    thuoc = await _thuoc(catalog_service, ctx, gia=Decimal("12000"))
    with pytest.raises(ValidationError):
        await catalog_service.set_drug_price(thuoc.id, Decimal("13500"), "   ", ctx)

    lai = await catalog_service.get_drug(thuoc.id, ctx)
    assert lai.sale_price == Decimal("12000")
    assert await _lich_su(session_factory, thuoc.id) == []


async def test_dat_gia_lan_dau_KHONG_doi_ly_do(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Mã nhập từ NPP chưa có giá thì lần đầu chốt giá không có gì để giải thích."""
    thuoc = await _thuoc(catalog_service, ctx)
    out = await catalog_service.set_drug_price(thuoc.id, Decimal("9000"), None, ctx)
    assert out.sale_price == Decimal("9000")


async def test_doi_gia_KHONG_ghi_de_ten_va_hoat_chat(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Bẫy `to_orm()`: dựng lại cả `DrugORM` thì một lượt đổi giá ghi đè mọi trường khác."""
    thuoc = await _thuoc(catalog_service, ctx, gia=Decimal("12000"))
    ten_cu = thuoc.name

    await catalog_service.set_drug_price(thuoc.id, Decimal("15000"), "khuyến mãi hết", ctx)

    lai = await catalog_service.get_drug(thuoc.id, ctx)
    assert lai.name == ten_cu
    assert lai.base_unit == "viên"
    assert lai.rx_class == "OTC"


async def test_gia_trung_gia_cu_bi_tu_choi(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    thuoc = await _thuoc(catalog_service, ctx, gia=Decimal("12000"))
    with pytest.raises(ValidationError):
        await catalog_service.set_drug_price(thuoc.id, Decimal("12000"), "không đổi gì", ctx)


async def test_thuoc_khong_ton_tai_tra_404(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await catalog_service.set_drug_price(uuid4(), Decimal("1000"), None, ctx)


async def test_khong_co_catalog_update_thi_khong_doi_duoc_gia(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Giá là quyết định CẤP CHUỖI (Chain chốt 31/07). `catalog.read` không đủ."""
    thuoc = await _thuoc(catalog_service, ctx)
    chi_doc = replace(ctx, permissions=frozenset({"catalog.read"}))
    with pytest.raises(PermissionDeniedError):
        await catalog_service.set_drug_price(thuoc.id, Decimal("1000"), None, chi_doc)


async def test_doc_lich_su_chi_can_catalog_read(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Giá niêm yết phải công khai tại nơi bán (Điều 107.4) — lịch sử không phải bí mật."""
    thuoc = await _thuoc(catalog_service, ctx)
    await catalog_service.set_drug_price(thuoc.id, Decimal("8000"), None, ctx)

    chi_doc = replace(ctx, permissions=frozenset({"catalog.read"}))
    lich_su = await catalog_service.drug_price_history(thuoc.id, chi_doc)
    assert [r.new_price for r in lich_su] == [Decimal("8000")]


async def test_lich_su_tra_ve_MOI_NHAT_TRUOC(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    thuoc = await _thuoc(catalog_service, ctx)
    await catalog_service.set_drug_price(thuoc.id, Decimal("1000"), None, ctx)
    await catalog_service.set_drug_price(thuoc.id, Decimal("2000"), "lần 2", ctx)
    await catalog_service.set_drug_price(thuoc.id, Decimal("3000"), "lần 3", ctx)

    lich_su = await catalog_service.drug_price_history(thuoc.id, ctx)
    assert [r.new_price for r in lich_su] == [
        Decimal("3000"),
        Decimal("2000"),
        Decimal("1000"),
    ]


async def test_doi_gia_ghi_mot_dong_audit(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Sổ audit là lớp THỨ HAI, độc lập với bảng lịch sử — mất một không suy ra được cái kia."""
    thuoc = await _thuoc(catalog_service, ctx, gia=Decimal("5000"))
    await catalog_service.set_drug_price(thuoc.id, Decimal("6000"), "điều chỉnh", ctx)

    async with session_factory() as session:
        rows = (
            await session.execute(
                select(AuditLogORM).where(
                    AuditLogORM.action == AuditAction.CATALOG_DRUG_PRICE_CHANGED.value,
                    AuditLogORM.target_id == str(thuoc.id),
                )
            )
        ).scalars()
        dong = list(rows)
    assert len(dong) == 1
