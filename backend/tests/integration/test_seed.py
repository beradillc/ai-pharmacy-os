from seeds.reference_data import (
    ATC_CODES,
    DRUG_INTERACTIONS,
    seed_atc_codes,
    seed_drug_interactions,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.modules.catalog.infrastructure import AtcCodeORM
from pharmacy_os.modules.clinical.infrastructure import DrugInteractionORM


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
