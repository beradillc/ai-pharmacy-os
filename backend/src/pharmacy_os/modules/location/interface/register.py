"""Compose module location: service + router."""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.db import UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.modules.location.application import LocationService
from pharmacy_os.modules.location.infrastructure import SqlAlchemyLocationRepository
from pharmacy_os.modules.location.interface.router import ContextDep, build_router


def register(container: Container, get_context: ContextDep) -> APIRouter:
    service = LocationService(
        container.resolve(UnitOfWorkFactory),
        lambda uow, ctx: SqlAlchemyLocationRepository(uow.session, ctx),
        container.resolve(AuditLogger),
    )
    container.register_instance(LocationService, service)
    return build_router(get_context)
