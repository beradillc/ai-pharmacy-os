from datetime import date
from decimal import Decimal

from seeds.reference_data import (
    ATC_CODES,
    DRUG_INTERACTIONS,
    seed_atc_codes,
    seed_controlled_substances,
    seed_drug_interactions,
)
from seeds.tt18_controlled_substances import CONTROLLED_SUBSTANCES_TT18
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.modules.catalog.infrastructure import AtcCodeORM
from pharmacy_os.modules.clinical.infrastructure import DrugInteractionORM
from pharmacy_os.modules.compliance.infrastructure import ControlledSubstanceORM


async def test_seed_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        first = await seed_atc_codes(session)
        await session.commit()
    assert first == len(ATC_CODES)

    # Second run inserts nothing.
    async with session_factory() as session:
        second = await seed_atc_codes(session)
        await session.commit()
        total = (await session.execute(select(func.count()).select_from(AtcCodeORM))).scalar_one()
    assert second == 0
    assert total == len(ATC_CODES)


async def test_seed_drug_interactions_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        first = await seed_drug_interactions(session)
        await session.commit()
    assert first == len(DRUG_INTERACTIONS)

    # Second run inserts nothing (idempotent by canonical ingredient pair).
    async with session_factory() as session:
        second = await seed_drug_interactions(session)
        await session.commit()
        total = (
            await session.execute(select(func.count()).select_from(DrugInteractionORM))
        ).scalar_one()
    assert second == 0
    assert total == len(DRUG_INTERACTIONS)


async def test_seed_controlled_substances_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    async with session_factory() as session:
        created, updated = await seed_controlled_substances(session)
        await session.commit()
    assert (created, updated) == (len(CONTROLLED_SUBSTANCES_TT18), 0)

    async with session_factory() as session:
        created, updated = await seed_controlled_substances(session)
        await session.commit()
        total = (
            await session.execute(select(func.count()).select_from(ControlledSubstanceORM))
        ).scalar_one()
    assert (created, updated) == (0, 0)
    assert total == len(CONTROLLED_SUBSTANCES_TT18)


async def test_seed_controlled_substances_ghi_de_dong_da_ton_tai(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Nhánh CẬP NHẬT — deployment cũ đã có dòng cho chất đó, ngưỡng pháp lý đổi.

    Kỷ luật 7 (CLAUDE.md): pytest luôn dựng CSDL rỗng nên chỉ đi nhánh insert. Test này
    ép đi nhánh còn lại — nếu seed chỉ "insert nếu thiếu" thì bản nâng cấp sẽ giữ ngưỡng
    cũ và phân loại sai thuốc dạng phối hợp.
    """
    async with session_factory() as session:
        await seed_controlled_substances(session)
        await session.commit()

    async with session_factory() as session:
        row = (
            await session.execute(
                select(ControlledSubstanceORM).where(ControlledSubstanceORM.name_intl == "TRAMADOL")
            )
        ).scalar_one()
        row.limit_per_unit_mg = Decimal("999")
        row.effective_from = date(1999, 1, 1)
        await session.commit()

    async with session_factory() as session:
        created, updated = await seed_controlled_substances(session)
        await session.commit()
        row = (
            await session.execute(
                select(ControlledSubstanceORM).where(ControlledSubstanceORM.name_intl == "TRAMADOL")
            )
        ).scalar_one()
    assert (created, updated) == (0, 1)
    assert row.limit_per_unit_mg == Decimal("37.5")  # TT18 Phụ lục IV
    assert row.effective_from is None


async def test_danh_muc_tt18_dung_so_luong_theo_van_ban(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Chốt số lượng từng phụ lục — văn bản đổi mà quên sinh lại dữ liệu thì test này đỏ."""
    async with session_factory() as session:
        await seed_controlled_substances(session)
        await session.commit()
        counts = dict(
            (
                await session.execute(
                    select(ControlledSubstanceORM.appendix, func.count()).group_by(
                        ControlledSubstanceORM.appendix
                    )
                )
            ).all()
        )
        co_nguong = (
            await session.execute(
                select(func.count())
                .select_from(ControlledSubstanceORM)
                .where(
                    (ControlledSubstanceORM.limit_per_unit_mg.is_not(None))
                    | (ControlledSubstanceORM.limit_concentration_pct.is_not(None))
                    | (ControlledSubstanceORM.limit_note.is_not(None))
                )
            )
        ).scalar_one()
        moc_rieng = (
            (
                await session.execute(
                    select(ControlledSubstanceORM.name_intl)
                    .where(ControlledSubstanceORM.effective_from.is_not(None))
                    .order_by(ControlledSubstanceORM.name_intl)
                )
            )
            .scalars()
            .all()
        )
    assert counts == {"PL_I": 42, "PL_II": 72, "PL_III": 8}
    assert co_nguong == 62  # PL IV 13 + PL V 43 + PL VI 6
    # TT18 Điều 16.2 — hướng thần từ 01/6/2026, sớm hơn hiệu lực chung 16/7/2026.
    assert list(moc_rieng) == ["CARISOPRODOL", "ETOMIDATE"]
