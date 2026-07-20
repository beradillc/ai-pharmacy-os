"""Run reference-data seeds against the configured database.

Usage (from ``backend/`` with the venv active and the DB migrated)::

    python -m seeds.run
"""

from __future__ import annotations

import asyncio

import structlog

from pharmacy_os.core.config import get_settings
from pharmacy_os.core.db import build_engine, build_sessionmaker
from seeds.reference_data import seed_atc_codes

_log = structlog.get_logger("seed")


async def main() -> None:
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    session_factory = build_sessionmaker(engine)
    async with session_factory() as session:
        count = await seed_atc_codes(session)
        await session.commit()
    await engine.dispose()
    _log.info("seed_complete", atc_codes_inserted=count)


if __name__ == "__main__":
    asyncio.run(main())
