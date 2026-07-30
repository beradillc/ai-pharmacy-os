"""`CatalogService.replace_drug_ingredients` — đường sửa hoạt chất, tầng app+infra.

Vì sao cần tầng này ngoài test domain: domain chỉ biết đổi một list trong bộ nhớ. Ba thứ
chỉ ở đây mới kiểm được, và cả ba đều là chỗ đã hỏng thật trong dự án này trước đây:

* **`cascade="all, delete-orphan"` có thật sự XOÁ dòng cũ** — hay chỉ chèn thêm, để lại
  dòng mồ côi vẫn kích hoạt cảnh báo dị ứng;
* **cổng này không được ghi đè trường khác** (tên/giá/mã vạch), vì `to_orm()` dựng lại cả
  `DrugORM` — đúng cái bẫy đã ghi trong docstring của `save_ingredients`;
* **quyền `catalog.update` tách khỏi `catalog.read`/`catalog.create`**.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction
from pharmacy_os.core.audit.models import AuditLogORM
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.catalog.application.dto import (
    CreateDrugInput,
    CreateIngredientInput,
    DrugIngredientInput,
    DrugOutput,
)
from pharmacy_os.modules.catalog.infrastructure.models import DrugIngredientORM


async def _hoat_chat(svc: CatalogService, ctx: RequestContext, ten: str) -> DrugIngredientInput:
    out = await svc.create_ingredient(CreateIngredientInput(name=f"{ten}-{uuid4().hex[:6]}"), ctx)
    return DrugIngredientInput(ingredient_id=out.id, amount=Decimal("500"), unit="mg")


async def _thuoc(
    svc: CatalogService,
    ctx: RequestContext,
    *hoat_chat: DrugIngredientInput,
    ten: str | None = None,
) -> DrugOutput:
    """Tạo thuốc và trả về **DrugOutput** — `CreateDrugInput` không mang id, id sinh trong
    domain lúc dựng aggregate."""
    return await svc.create_drug(
        CreateDrugInput(
            name=ten or f"Thuốc-{uuid4().hex[:6]}",
            rx_class="OTC",
            base_unit="viên",
            ingredients=list(hoat_chat),
        ),
        ctx,
    )


async def _dem_dong(session_factory: async_sessionmaker[AsyncSession], drug_id: object) -> int:
    async with session_factory() as session:
        return int(
            (
                await session.execute(
                    select(func.count())
                    .select_from(DrugIngredientORM)
                    .where(DrugIngredientORM.drug_id == drug_id)
                )
            ).scalar_one()
        )


async def test_thay_hoat_chat_XOA_HAN_dong_cu_trong_CSDL(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """🔴 Phép kiểm quan trọng nhất của bước này.

    Nếu `cascade="all, delete-orphan"` không xoá mà chỉ chèn thêm, thuốc sẽ mang **cả**
    hoạt chất cũ lẫn mới — và cảnh báo dị ứng vẫn kêu theo hoạt chất đã bị bỏ. Đếm dòng
    thật trong bảng, không đọc lại qua service (service đọc qua cùng ORM đã nạp sẵn).
    """
    cu = await _hoat_chat(catalog_service, ctx, "Cũ")
    data = await _thuoc(catalog_service, ctx, cu)
    assert await _dem_dong(session_factory, data.id) == 1

    moi = await _hoat_chat(catalog_service, ctx, "Mới")
    out = await catalog_service.replace_drug_ingredients(data.id, [moi], ctx)

    assert [i.ingredient_id for i in out.ingredients] == [moi.ingredient_id]
    assert await _dem_dong(session_factory, data.id) == 1  # 1, không phải 2


async def test_danh_sach_rong_xoa_sach_bang(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data = await _thuoc(
        catalog_service,
        ctx,
        await _hoat_chat(catalog_service, ctx, "A"),
        await _hoat_chat(catalog_service, ctx, "B"),
    )
    assert await _dem_dong(session_factory, data.id) == 2
    await catalog_service.replace_drug_ingredients(data.id, [], ctx)
    assert await _dem_dong(session_factory, data.id) == 0


async def test_them_hoat_chat_cho_thuoc_dang_TRONG(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Ca §7ce ngoài đời: thuốc đã tạo mà không nối hoạt chất nào."""
    data = await _thuoc(catalog_service, ctx)
    hc = await _hoat_chat(catalog_service, ctx, "Paracetamol")
    out = await catalog_service.replace_drug_ingredients(data.id, [hc], ctx)
    assert [i.ingredient_id for i in out.ingredients] == [hc.ingredient_id]


async def test_KHONG_duoc_ghi_de_ten_gia_ma_vach(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """🔴 Cổng hẹp: sửa hoạt chất không được đụng trường nào khác.

    `to_orm()` dựng lại cả `DrugORM` từ aggregate, nên một cài đặt dùng `merge()` sẽ ghi
    đè tên/giá/mã vạch mà không ai yêu cầu. Đây là bẫy đã ghi thẳng trong docstring của
    `save_ingredients` — và test này là thứ giữ nó đúng.
    """
    data = CreateDrugInput(
        name=f"Tên-Gốc-{uuid4().hex[:6]}",
        rx_class="ETC",
        base_unit="viên",
        barcode=f"BC{uuid4().hex[:10]}",
        sale_price=Decimal("12500"),
        strength="500mg",
    )
    truoc = await catalog_service.create_drug(data, ctx)
    hc = await _hoat_chat(catalog_service, ctx, "X")
    await catalog_service.replace_drug_ingredients(truoc.id, [hc], ctx)

    sau = await catalog_service.get_drug(truoc.id, ctx)
    assert sau.name == data.name
    assert sau.barcode == data.barcode
    assert sau.sale_price == data.sale_price
    assert sau.rx_class == "ETC"
    assert sau.strength == "500mg"


async def test_giu_dung_ham_luong_va_don_vi_moi(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Sửa hàm lượng nhập sai — cùng hoạt chất, số khác."""
    hc = await _hoat_chat(catalog_service, ctx, "Amoxicillin")
    data = await _thuoc(catalog_service, ctx, hc)
    out = await catalog_service.replace_drug_ingredients(
        data.id, [replace(hc, amount=Decimal("875"), unit="mg")], ctx
    )
    assert out.ingredients[0].amount == Decimal("875")
    assert out.ingredients[0].unit == "mg"


async def test_thuoc_khong_ton_tai_thi_404(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    with pytest.raises(NotFoundError):
        await catalog_service.replace_drug_ingredients(uuid4(), [], ctx)


async def test_hoat_chat_khong_ton_tai_thi_404_va_GIU_NGUYEN_danh_sach_cu(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Id sai ở CUỐI danh sách vẫn không được xoá mất danh sách cũ **trong CSDL**.

    Ghi rõ giới hạn của phép kiểm này, vì tôi đã tưởng sai một lần: nó **không** chứng minh
    được thứ tự "kiểm tồn tại trước, đổi aggregate sau" trong service. Đảo thứ tự đó thì
    test này vẫn xanh (đã đo bằng đột biến 30/07) — aggregate bị vứt đi khi exception ném
    ra, chưa kịp tới `save_ingredients`. Thứ nó thật sự canh là: một id sai bất kỳ chỗ nào
    trong danh sách ⇒ **không dòng nào trong CSDL đổi**.
    """
    cu = await _hoat_chat(catalog_service, ctx, "Cũ")
    data = await _thuoc(catalog_service, ctx, cu)
    hop_le = await _hoat_chat(catalog_service, ctx, "Hợp lệ")
    with pytest.raises(NotFoundError):
        await catalog_service.replace_drug_ingredients(
            data.id,
            [hop_le, DrugIngredientInput(ingredient_id=uuid4(), amount=Decimal("1"), unit="mg")],
            ctx,
        )
    assert await _dem_dong(session_factory, data.id) == 1
    con_lai = await catalog_service.get_drug(data.id, ctx)
    assert [i.ingredient_id for i in con_lai.ingredients] == [cu.ingredient_id]


async def test_trung_hoat_chat_thi_422(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    data = await _thuoc(catalog_service, ctx)
    hc = await _hoat_chat(catalog_service, ctx, "Trùng")
    with pytest.raises(ValidationError):
        await catalog_service.replace_drug_ingredients(data.id, [hc, hc], ctx)


async def test_ham_luong_khong_duong_thi_422(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    data = await _thuoc(catalog_service, ctx)
    hc = await _hoat_chat(catalog_service, ctx, "Âm")
    with pytest.raises(ValidationError):
        await catalog_service.replace_drug_ingredients(
            data.id, [replace(hc, amount=Decimal("0"))], ctx
        )


async def test_thuoc_cua_tenant_KHAC_thi_404_khong_sua_duoc(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """Cách ly tenant: thuốc của nhà thuốc khác phải vô hình, không phải "sửa được"."""
    data = await _thuoc(catalog_service, ctx)
    ctx_khac = replace(ctx, tenant_id=uuid4())
    with pytest.raises(NotFoundError):
        await catalog_service.replace_drug_ingredients(data.id, [], ctx_khac)


async def test_chi_co_catalog_read_thi_BI_TU_CHOI(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """🔴 Đọc danh mục là việc thường ngày ở quầy; sửa hoạt chất đổi hành vi cảnh báo dị
    ứng của toàn chuỗi. Hai quyền khác nhau."""
    data = await _thuoc(catalog_service, ctx)
    chi_doc = replace(ctx, permissions=frozenset({"catalog.read"}))
    with pytest.raises(PermissionDeniedError):
        await catalog_service.replace_drug_ingredients(data.id, [], chi_doc)


async def test_co_catalog_create_nhung_khong_co_update_thi_BI_TU_CHOI(
    catalog_service: CatalogService, ctx: RequestContext
) -> None:
    """🔴 Phép kiểm phân biệt hai quyền — nếu service dùng chung `catalog.create` thì test
    này xanh vì lý do sai và không ai biết quyền mới chưa được nối."""
    data = await _thuoc(catalog_service, ctx)
    tao_thoi = replace(ctx, permissions=frozenset({"catalog.read", "catalog.create"}))
    with pytest.raises(PermissionDeniedError):
        await catalog_service.replace_drug_ingredients(data.id, [], tao_thoi)


async def test_ghi_vet_audit_kem_so_luong_TRUOC_va_SAU(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """🔴 Bỏ hoạt chất khỏi một thuốc là cách duy nhất làm cảnh báo dị ứng ngừng kêu, và
    không có gì khác trong hệ thống ghi lại việc đó. Dòng `2 → 0` là toàn bộ tín hiệu.
    """
    data = await _thuoc(
        catalog_service,
        ctx,
        await _hoat_chat(catalog_service, ctx, "A"),
        await _hoat_chat(catalog_service, ctx, "B"),
    )
    await catalog_service.replace_drug_ingredients(data.id, [], ctx)

    async with session_factory() as session:
        row = (
            await session.execute(
                select(AuditLogORM).where(
                    AuditLogORM.action == AuditAction.CATALOG_DRUG_INGREDIENTS_REPLACED.value,
                    AuditLogORM.target_id == str(data.id),
                )
            )
        ).scalar_one()
    assert row.actor_user_id == ctx.user_id
    assert row.target_type == "drug"
    assert row.context["count_before"] == "2"
    assert row.context["count_after"] == "0"


async def test_audit_KHONG_chep_id_hoat_chat_vao_so(
    catalog_service: CatalogService,
    ctx: RequestContext,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Sổ audit chứng minh việc truy cập đã xảy ra, không phải bản sao thứ hai của dữ liệu
    nó canh (NĐ 356/2025 Điều 4.2). Số đếm là metadata; danh sách là nội dung."""
    hc = await _hoat_chat(catalog_service, ctx, "Kín")
    data = await _thuoc(catalog_service, ctx)
    await catalog_service.replace_drug_ingredients(data.id, [hc], ctx)

    async with session_factory() as session:
        row = (
            await session.execute(
                select(AuditLogORM).where(
                    AuditLogORM.action == AuditAction.CATALOG_DRUG_INGREDIENTS_REPLACED.value,
                    AuditLogORM.target_id == str(data.id),
                )
            )
        ).scalar_one()
    assert str(hc.ingredient_id) not in str(row.context)
