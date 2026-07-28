"""Compose the sales module: build its service and router.

Cross-module reactions (inventory dispensing on ``SaleCompleted``) are wired at
the API composition root, not here — sales never imports inventory.
"""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork, UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.core.plugins import HookRegistry
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.domain import DrugInfoProvider, PrescriptionInfoProvider
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository
from pharmacy_os.modules.sales.interface.router import ContextDep, build_router


def register(
    container: Container,
    get_context: ContextDep,
    drug_info: DrugInfoProvider | None = None,
    prescription_info: PrescriptionInfoProvider | None = None,
) -> APIRouter:
    uow_factory = container.resolve(UnitOfWorkFactory)

    def repo_factory(uow: UnitOfWork, ctx: RequestContext) -> SqlAlchemySalesRepository:
        return SqlAlchemySalesRepository(uow.session, ctx)

    service = SalesService(
        uow_factory,
        repo_factory,
        drug_info,
        prescription_info,
        container.resolve(AuditLogger),
        container.resolve(HookRegistry),
        container.resolve(Settings).plugins.call_timeout_seconds,
    )
    container.register_instance(SalesService, service)
    return build_router(get_context)
