"""Compose the compliance module: build its service and router.

``NationalSyncService`` is registered separately by ``wire_national_sync`` at the composition
root (it must be resolvable for the cross-module sale-completed subscriber too) — this only
builds and registers ``ComplianceService``, then wires both into the router. Callers must run
``wire_national_sync`` first.
"""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import UnitOfWork, UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.modules.compliance.application import ComplianceService
from pharmacy_os.modules.compliance.domain.ports import DrugMasterProvider, SigningReauthProvider
from pharmacy_os.modules.compliance.infrastructure import (
    SqlAlchemyControlledLedgerRepository,
    SqlAlchemyDrugReturnRecordRepository,
    SqlAlchemyLedgerBookSignatureRepository,
    SqlAlchemyTenantComplianceConfigRepository,
)
from pharmacy_os.modules.compliance.interface.router import ContextDep, build_router


def register(
    container: Container,
    get_context: ContextDep,
    drug_master: DrugMasterProvider | None = None,
    reauth: SigningReauthProvider | None = None,
) -> APIRouter:
    """``drug_master``/``reauth`` optional so existing callers/tests that don't need the Mẫu
    số 06 periodic report (docs/13 mục C.7) or bước 6 ký sổ (mục C.5) keep working unchanged;
    the real adapters are wired at the composition root (``api/v1/__init__.py``), same pattern
    as sales' ``drug_info``.
    """
    uow_factory = container.resolve(UnitOfWorkFactory)

    def ledger_repo_factory(
        uow: UnitOfWork, ctx: RequestContext
    ) -> SqlAlchemyControlledLedgerRepository:
        return SqlAlchemyControlledLedgerRepository(uow.session, ctx)

    def config_repo_factory(
        uow: UnitOfWork, ctx: RequestContext
    ) -> SqlAlchemyTenantComplianceConfigRepository:
        return SqlAlchemyTenantComplianceConfigRepository(uow.session, ctx)

    def drug_return_repo_factory(
        uow: UnitOfWork, ctx: RequestContext
    ) -> SqlAlchemyDrugReturnRecordRepository:
        return SqlAlchemyDrugReturnRecordRepository(uow.session, ctx)

    def signature_repo_factory(
        uow: UnitOfWork, ctx: RequestContext
    ) -> SqlAlchemyLedgerBookSignatureRepository:
        return SqlAlchemyLedgerBookSignatureRepository(uow.session, ctx)

    service = ComplianceService(
        uow_factory,
        ledger_repo_factory,
        config_repo_factory,
        container.resolve(AuditLogger),
        drug_master,
        drug_return_repo_factory,
        signature_repo_factory,
        reauth,
    )
    container.register_instance(ComplianceService, service)
    return build_router(get_context)
