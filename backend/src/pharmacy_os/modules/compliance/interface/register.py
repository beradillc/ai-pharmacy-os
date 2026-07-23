"""Compose the compliance module: build its service and router.

``NationalSyncService`` is registered separately by ``wire_national_sync`` at the composition
root (it must be resolvable for the cross-module sale-completed subscriber too) — this only
builds and registers ``ComplianceService``, then wires both into the router. Callers must run
``wire_national_sync`` first.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus
from pharmacy_os.modules.compliance.application import ComplianceService
from pharmacy_os.modules.compliance.infrastructure import (
    SqlAlchemyControlledLedgerRepository,
    SqlAlchemyTenantComplianceConfigRepository,
)
from pharmacy_os.modules.compliance.interface.router import ContextDep, build_router


def register(container: Container, get_context: ContextDep) -> APIRouter:
    session_factory = container.resolve(async_sessionmaker[AsyncSession])
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    def ledger_repo_factory(
        uow: UnitOfWork, ctx: RequestContext
    ) -> SqlAlchemyControlledLedgerRepository:
        return SqlAlchemyControlledLedgerRepository(uow.session, ctx)

    def config_repo_factory(
        uow: UnitOfWork, ctx: RequestContext
    ) -> SqlAlchemyTenantComplianceConfigRepository:
        return SqlAlchemyTenantComplianceConfigRepository(uow.session, ctx)

    service = ComplianceService(
        uow_factory, ledger_repo_factory, config_repo_factory, container.resolve(AuditLogger)
    )
    container.register_instance(ComplianceService, service)
    return build_router(get_context)
