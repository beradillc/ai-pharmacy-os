"""Run reference-data seeds against the configured database.

Usage (from ``backend/`` with the venv active and the DB migrated)::

    python -m seeds.run
"""

from __future__ import annotations

import asyncio

import structlog

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import get_settings
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.iam.application import IamService
from pharmacy_os.modules.iam.interface import build_repositories
from seeds.reference_data import seed_atc_codes, seed_drug_interactions

_log = structlog.get_logger("seed")


async def main() -> None:
    settings = get_settings()
    engine = build_engine(settings.db.url, pool_size=settings.db.pool_size)
    session_factory = build_sessionmaker(engine)
    async with session_factory() as session:
        atc_count = await seed_atc_codes(session)
        interaction_count = await seed_drug_interactions(session)
        await session.commit()

    # System roles are code-owned, so a release that adds a permission reaches an
    # already-provisioned deployment only if something rewrites the existing rows.
    # Running it here means `make seed` after an upgrade is enough (idempotent).
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, InMemoryEventBus())

    roles = await IamService(
        uow_factory, build_repositories, AuditLogger(session_factory)
    ).sync_system_roles()

    await engine.dispose()
    _log.info(
        "seed_complete",
        atc_codes_inserted=atc_count,
        drug_interactions_inserted=interaction_count,
        system_roles_created=roles.created,
        system_roles_updated=roles.updated,
    )


if __name__ == "__main__":
    asyncio.run(main())
