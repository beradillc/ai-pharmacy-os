"""Nối thuốc → hoạt chất cho CSDL đã seed TRƯỚC khi seeder biết nối (PROJECT_STATE §7ce).

**Vì sao cần lệnh này, sửa seeder là chưa đủ.** Seeder đã vá ở `1bd4d4a`, nhưng nó chỉ
chạy khi seed **mới**. `nt650v2` — CSDL Chain đang bấm thử — vẫn 0 dòng `drug_ingredients`,
nghĩa là cảnh báo dị ứng ở đó **im lặng hoàn toàn**, kể cả với hai khách đã khai dị ứng
thật. Đường còn lại là seed lại từ đầu, nhưng như vậy mất 595 hoá đơn và chính hai bản khai
dị ứng đó — tức mất đúng dữ liệu cần để thử tính năng.

**Vì sao là lệnh chứ không phải migration.** Migration chạy trên schema, không biết *tenant
nào có thuốc tên gì*; ánh xạ ở đây khớp theo **tên thuốc**, là dữ liệu, không phải cấu trúc.
Đặt vào migration còn khiến nó chạy trên mọi deployment kể cả nơi dược sĩ đã tự nhập hoạt
chất bằng tay — chuyện phải do người quyết, không phải do `alembic upgrade` quyết.

**Chỉ THÊM, không bao giờ xoá hay sửa.** Một dòng đã có thì bỏ qua, kể cả khi hàm lượng
khác `1`: dòng đó có thể do dược sĩ nhập tay với hàm lượng thật, và ghi đè nó bằng `1` là
làm dữ liệu tệ đi. Vì vậy lệnh **an toàn khi chạy lại** và an toàn khi chạy trên CSDL đã
được vá một phần.

**Hàm lượng ghi `1` + đơn vị lẻ của thuốc.** Đây là điều lệnh này *không* biết: bảng ánh xạ
chỉ ghi *có hoạt chất nào*, không ghi mg. Cảnh báo dị ứng khớp theo `ingredient_id` nên
không cần liều — nhưng ai đọc bảng sau này cần biết con số đó là **chỗ giữ chỗ**, không phải
hàm lượng đã tra.

Cách chạy (từ `backend/`, venv đã bật, `DB__URL` trỏ đúng CSDL cần vá)::

    DB__URL=postgresql+asyncpg://pharma:pharma@localhost:5432/nt650v2 \\
        python -m seeds.backfill_drug_ingredients --verify    # đo trước, chưa ghi gì
    DB__URL=... python -m seeds.backfill_drug_ingredients --dry-run  # xem sẽ chèn gì
    DB__URL=... python -m seeds.backfill_drug_ingredients            # ghi thật

`--verify` trả **mã thoát 1** khi còn thuốc trong bảng ánh xạ mà chưa có hoạt chất nào —
tức nó là một **cổng** đúng nghĩa: đỏ trước khi vá, xanh sau khi vá (kỷ luật #14).
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.config import get_settings
from pharmacy_os.core.db import build_engine, build_sessionmaker
from pharmacy_os.modules.catalog.infrastructure.models import (
    ActiveIngredientORM,
    DrugIngredientORM,
    DrugORM,
)
from seeds.drug_ingredient_map import DRUG_INGREDIENTS

_log = structlog.get_logger("backfill_drug_ingredients")

#: Hàm lượng giữ chỗ — xem docstring module. KHÔNG phải hàm lượng đã tra.
_PLACEHOLDER_AMOUNT = Decimal("1")


@dataclass(frozen=True, slots=True)
class _Drug:
    """Chỉ ba thứ hàm lập kế hoạch cần biết về một thuốc."""

    id: UUID
    name: str
    base_unit: str


@dataclass(frozen=True, slots=True)
class _Row:
    drug_id: UUID
    ingredient_id: UUID
    unit: str


@dataclass(slots=True)
class _Plan:
    rows: list[_Row] = field(default_factory=list)
    """Những dòng sẽ chèn."""

    thieu_hoat_chat: dict[str, list[str]] = field(default_factory=dict)
    """Thuốc → hoạt chất bảng ánh xạ đòi mà danh mục hoạt chất KHÔNG có.

    Không tự tạo hoạt chất mới: thêm một hoạt chất là thêm dữ liệu tham chiếu **toàn hệ
    thống** (`active_ingredients` không có `tenant_id`), và nó có thể trùng tên khác chính
    tả với dòng đã có. Đó là quyết định, không phải hệ quả của một lệnh vá.
    """

    ngoai_bang: list[str] = field(default_factory=list)
    """Thuốc trong CSDL mà bảng ánh xạ không nhắc tới — 3 vật tư + 7 mã chờ Chain quyết."""

    da_co: int = 0
    """Số cặp (thuốc, hoạt chất) đã tồn tại ⇒ bỏ qua. Chạy lại lần hai thì bằng `rows` lần một."""


def build_plan(
    drugs: list[_Drug],
    ingredient_ids: dict[str, UUID],
    existing: set[tuple[UUID, UUID]],
) -> _Plan:
    """Quyết định chèn gì — **thuần**, không chạm CSDL, nên test được trực tiếp.

    Đây là toàn bộ phần có thể sai về mặt logic; phần còn lại của module chỉ là đọc/ghi.
    """
    plan = _Plan()
    for drug in drugs:
        ten_hoat_chat = DRUG_INGREDIENTS.get(drug.name)
        if ten_hoat_chat is None:
            plan.ngoai_bang.append(drug.name)
            continue
        for ten in ten_hoat_chat:
            ing_id = ingredient_ids.get(ten)
            if ing_id is None:
                plan.thieu_hoat_chat.setdefault(drug.name, []).append(ten)
                continue
            if (drug.id, ing_id) in existing:
                plan.da_co += 1
                continue
            plan.rows.append(_Row(drug_id=drug.id, ingredient_id=ing_id, unit=drug.base_unit))
    return plan


async def _read_state(
    session: AsyncSession, tenant_id: UUID
) -> tuple[list[_Drug], dict[str, UUID], set[tuple[UUID, UUID]]]:
    drugs = [
        _Drug(id=r.id, name=r.name, base_unit=r.base_unit)
        for r in (
            await session.execute(
                select(DrugORM.id, DrugORM.name, DrugORM.base_unit).where(
                    DrugORM.tenant_id == tenant_id
                )
            )
        ).all()
    ]
    ingredient_ids = {
        r.name: r.id
        for r in (
            await session.execute(select(ActiveIngredientORM.id, ActiveIngredientORM.name))
        ).all()
    }
    # Chỉ những cặp thuộc tenant này — `drug_ingredients` không có `tenant_id`, nó
    # thừa hưởng phạm vi qua `drug_id`, nên phải join chứ không quét cả bảng.
    existing = {
        (r.drug_id, r.ingredient_id)
        for r in (
            await session.execute(
                select(DrugIngredientORM.drug_id, DrugIngredientORM.ingredient_id)
                .join(DrugORM, DrugORM.id == DrugIngredientORM.drug_id)
                .where(DrugORM.tenant_id == tenant_id)
            )
        ).all()
    }
    return drugs, ingredient_ids, existing


async def _tenant_ids(session: AsyncSession) -> list[UUID]:
    """Lấy tenant từ chính bảng `drugs` — không cần nhập model `iam` chỉ để đếm tenant."""
    rows = (await session.execute(select(DrugORM.tenant_id).distinct())).scalars().all()
    return sorted(rows, key=str)


def _in_bao_cao(tenant_id: UUID, plan: _Plan, *, ghi_that: bool) -> None:
    dong = "đã chèn" if ghi_that else "sẽ chèn"
    print(  # noqa: T201
        f"\ntenant {tenant_id}\n"
        f"  {dong:9} {len(plan.rows):4} dòng · đã có sẵn {plan.da_co} · "
        f"ngoài bảng ánh xạ {len(plan.ngoai_bang)} thuốc"
    )
    if plan.ngoai_bang:
        print(f"  ngoài bảng: {', '.join(sorted(plan.ngoai_bang))}")  # noqa: T201
    for ten_thuoc, thieu in sorted(plan.thieu_hoat_chat.items()):
        print(  # noqa: T201
            f"  🔴 {ten_thuoc}: danh mục hoạt chất KHÔNG có {', '.join(thieu)} — "
            "phải thêm hoạt chất trước, lệnh này không tự tạo"
        )


async def _run(*, dry_run: bool, verify: bool) -> int:
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    session_factory = build_sessionmaker(engine)
    tong_chen = tong_thieu = 0
    try:
        async with session_factory() as session:
            tenants = await _tenant_ids(session)
            if not tenants:
                print("Không có thuốc nào trong CSDL này — không có gì để nối.")  # noqa: T201
                return 0

            for tenant_id in tenants:
                drugs, ingredient_ids, existing = await _read_state(session, tenant_id)
                plan = build_plan(drugs, ingredient_ids, existing)

                if verify:
                    # Cổng: thuốc CÓ trong bảng ánh xạ mà chưa có dòng hoạt chất nào.
                    chua_noi = sorted(
                        d.name
                        for d in drugs
                        if d.name in DRUG_INGREDIENTS and not any(k[0] == d.id for k in existing)
                    )
                    co_noi = len([d for d in drugs if d.name in DRUG_INGREDIENTS]) - len(chua_noi)
                    print(  # noqa: T201
                        f"\ntenant {tenant_id}\n"
                        f"  đã nối {co_noi} · CHƯA nối {len(chua_noi)} "
                        f"(trên {len(drugs)} thuốc, {plan.da_co} cặp đang có)"
                    )
                    if chua_noi:
                        print(f"  🔴 chưa nối: {', '.join(chua_noi)}")  # noqa: T201
                    tong_thieu += len(chua_noi)
                    continue

                _in_bao_cao(tenant_id, plan, ghi_that=not dry_run)
                tong_thieu += sum(len(v) for v in plan.thieu_hoat_chat.values())
                tong_chen += len(plan.rows)

                if plan.rows and not dry_run:
                    session.add_all(
                        DrugIngredientORM(
                            drug_id=r.drug_id,
                            ingredient_id=r.ingredient_id,
                            amount=_PLACEHOLDER_AMOUNT,
                            unit=r.unit,
                        )
                        for r in plan.rows
                    )
                    await session.commit()
                    _log.info("backfill.committed", tenant=str(tenant_id), rows=len(plan.rows))
    finally:
        await engine.dispose()

    if verify:
        print(  # noqa: T201
            f"\nTổng: {tong_thieu} thuốc chưa nối."
            + (
                "\n✅ Mọi thuốc trong bảng ánh xạ đều đã có hoạt chất."
                if tong_thieu == 0
                else "\n🔴 CÒN THUỐC CHƯA NỐI — cảnh báo dị ứng sẽ im lặng ở những mã này."
            )
        )
        return 1 if tong_thieu else 0

    print(  # noqa: T201
        f"\nTổng: {'sẽ chèn' if dry_run else 'đã chèn'} {tong_chen} dòng."
        + ("\n(--dry-run: chưa ghi gì)" if dry_run else "\nChạy --verify để kiểm chứng.")
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Nối thuốc → hoạt chất cho CSDL đã seed trước khi seeder biết nối."
    )
    parser.add_argument("--dry-run", action="store_true", help="Chỉ báo sẽ chèn gì, không ghi")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Đếm thuốc chưa nối; trả mã thoát 1 nếu còn (dùng làm cổng)",
    )
    args = parser.parse_args(argv)
    return asyncio.run(_run(dry_run=args.dry_run, verify=args.verify))


if __name__ == "__main__":
    raise SystemExit(main())
