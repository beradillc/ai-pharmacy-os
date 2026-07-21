"""Compose the prescription module: build its service and router."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.di import Container
from pharmacy_os.core.events import EventBus
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.infrastructure import SqlAlchemyPrescriptionRepository
from pharmacy_os.modules.prescription.interface.router import ContextDep, build_router


def register(container: Container, get_context: ContextDep) -> APIRouter:
    session_factory = container.resolve(async_sessionmaker[AsyncSession])
    event_bus = container.resolve(EventBus)  # type: ignore[type-abstract]

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    def repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemyPrescriptionRepository:
        return SqlAlchemyPrescriptionRepository(uow.session, ctx)

    service = PrescriptionService(uow_factory, repo_factory)
    container.register_instance(PrescriptionService, service)
    return build_router(get_context)
