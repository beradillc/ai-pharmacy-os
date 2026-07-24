"""Compose the prescription module: build its service and router."""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork, UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.infrastructure import SqlAlchemyPrescriptionRepository
from pharmacy_os.modules.prescription.interface.router import ContextDep, build_router


def register(container: Container, get_context: ContextDep) -> APIRouter:
    uow_factory = container.resolve(UnitOfWorkFactory)

    def repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemyPrescriptionRepository:
        return SqlAlchemyPrescriptionRepository(uow.session, ctx)

    service = PrescriptionService(uow_factory, repo_factory, container.resolve(AuditLogger))
    container.register_instance(PrescriptionService, service)
    return build_router(get_context)
