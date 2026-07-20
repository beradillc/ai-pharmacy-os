from seeds.reference_data import ATC_CODES, seed_atc_codes
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.modules.catalog.infrastructure import AtcCodeORM


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
