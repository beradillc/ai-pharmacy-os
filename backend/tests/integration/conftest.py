"""Integration fixtures: a real (SQLite in-memory) DB and wired services."""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from pharmacy_os.core.ai import MockLLMProvider
from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.core.security import JwtService
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.catalog.application import CatalogService
from pharmacy_os.modules.catalog.infrastructure import (
    SqlAlchemyActiveIngredientRepository,
    SqlAlchemyDrugRepository,
)
from pharmacy_os.modules.clinical.application import ClinicalService
from pharmacy_os.modules.clinical.infrastructure import (
    SqlAlchemyAiRecommendationRepository,
    SqlAlchemyDrugInteractionRepository,
    SqlAlchemyTenantAiSettingsRepository,
)
from pharmacy_os.modules.compliance.application import ComplianceService
from pharmacy_os.modules.compliance.infrastructure import (
    SqlAlchemyControlledLedgerRepository,
    SqlAlchemyTenantComplianceConfigRepository,
)
from pharmacy_os.modules.crm.application import CrmService
from pharmacy_os.modules.crm.infrastructure import SqlAlchemyCustomerRepository
from pharmacy_os.modules.iam.application import AuthService, IamRepositories, IamService
from pharmacy_os.modules.iam.infrastructure import (
    SqlAlchemyBranchRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyRoleAssignmentRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyUserRepository,
)
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.infrastructure import (
    SqlAlchemyBalanceRepository,
    SqlAlchemyBatchRepository,
    SqlAlchemyMovementRepository,
    SqlAlchemyStockReconciliationRepository,
)
from pharmacy_os.modules.prescription.application import PrescriptionService
from pharmacy_os.modules.prescription.infrastructure import SqlAlchemyPrescriptionRepository
from pharmacy_os.modules.procurement.application import ProcurementService
from pharmacy_os.modules.procurement.infrastructure import (
    SqlAlchemyGoodsReceiptRepository,
    SqlAlchemyPurchaseOrderRepository,
    SqlAlchemySupplierRepository,
)
from pharmacy_os.modules.sales.application import SalesService
from pharmacy_os.modules.sales.infrastructure import SqlAlchemySalesRepository


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # SQLite ignores FK constraints unless told to per-connection; enable so
    # cross-module FKs (e.g. customer_allergies.ingredient_id) behave like Postgres.
    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: object, connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    await engine.dispose()


@pytest.fixture
def event_bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.fixture
def ctx() -> RequestContext:
    return RequestContext(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
        permissions=frozenset(
            {
                "catalog.read",
                "catalog.create",
                "inventory.read",
                "inventory.receive",
                "inventory.dispense",
                "inventory.reconcile",
                "sales.read",
                "sales.create",
                "sales.return",
                "rx.read",
                "rx.create",
                "rx.approve",
                "rx.dispense",
                "compliance.ledger.read",
                "compliance.ledger.write",
                "compliance.config.read",
                "compliance.config.write",
                "compliance.sync.push",
                "compliance.sync.read",
                "clinical.check",
                "clinical.accept",
                "clinical.settings.read",
                "clinical.settings.write",
                "crm.create",
                "crm.read",
                "crm.write",
                "crm.consent.manage",
                "crm.sensitive.read",
                "crm.sensitive.write",
                "crm.erase",
                "procurement.supplier.create",
                "procurement.supplier.read",
                "procurement.po.create",
                "procurement.po.read",
                "procurement.po.write",
                "procurement.grn.create",
                "procurement.grn.read",
                "procurement.grn.confirm",
            }
        ),
    )


@pytest.fixture
def catalog_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> CatalogService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return CatalogService(
        uow_factory,
        lambda uow, c: SqlAlchemyDrugRepository(uow.session, c),
        lambda uow: SqlAlchemyActiveIngredientRepository(uow.session),
        AuditLogger(session_factory),
    )


@pytest.fixture
def inventory_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> InventoryService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return InventoryService(
        uow_factory,
        lambda uow, c: SqlAlchemyBatchRepository(uow.session, c),
        lambda uow, c: SqlAlchemyMovementRepository(uow.session, c),
        lambda uow, c: SqlAlchemyBalanceRepository(uow.session, c),
        lambda uow, c: SqlAlchemyStockReconciliationRepository(uow.session, c),
        AuditLogger(session_factory),
    )


@pytest.fixture
def sales_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> SalesService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return SalesService(
        uow_factory,
        lambda uow, c: SqlAlchemySalesRepository(uow.session, c),
        audit=AuditLogger(session_factory),
    )


@pytest.fixture
def prescription_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> PrescriptionService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return PrescriptionService(
        uow_factory,
        lambda uow, c: SqlAlchemyPrescriptionRepository(uow.session, c),
        AuditLogger(session_factory),
    )


@pytest.fixture
def compliance_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> ComplianceService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return ComplianceService(
        uow_factory,
        lambda uow, c: SqlAlchemyControlledLedgerRepository(uow.session, c),
        lambda uow, c: SqlAlchemyTenantComplianceConfigRepository(uow.session, c),
        AuditLogger(session_factory),
    )


@pytest.fixture
def clinical_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> ClinicalService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return ClinicalService(
        uow_factory,
        lambda uow: SqlAlchemyDrugInteractionRepository(uow.session),
        lambda uow, c: SqlAlchemyAiRecommendationRepository(uow.session, c),
        lambda uow, c: SqlAlchemyTenantAiSettingsRepository(uow.session, c),
        MockLLMProvider(),
        min_confidence=0.6,
        audit=AuditLogger(session_factory),
    )


@pytest.fixture
def crm_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> CrmService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return CrmService(
        uow_factory,
        lambda uow, c: SqlAlchemyCustomerRepository(uow.session, c),
        AuditLogger(session_factory),
    )


@pytest.fixture
def procurement_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> ProcurementService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return ProcurementService(
        uow_factory,
        lambda uow, c: SqlAlchemySupplierRepository(uow.session, c),
        lambda uow, c: SqlAlchemyPurchaseOrderRepository(uow.session, c),
        lambda uow, c: SqlAlchemyGoodsReceiptRepository(uow.session, c),
        AuditLogger(session_factory),
    )


def _iam_repos(uow: UnitOfWork) -> IamRepositories:
    return IamRepositories(
        tenants=SqlAlchemyTenantRepository(uow.session),
        branches=SqlAlchemyBranchRepository(uow.session),
        users=SqlAlchemyUserRepository(uow.session),
        roles=SqlAlchemyRoleRepository(uow.session),
        assignments=SqlAlchemyRoleAssignmentRepository(uow.session),
        sessions=SqlAlchemyRefreshTokenRepository(uow.session),
    )


@pytest.fixture
def iam_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> IamService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return IamService(uow_factory, _iam_repos, AuditLogger(session_factory))


@pytest.fixture
def auth_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> AuthService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return AuthService(
        uow_factory,
        _iam_repos,
        JwtService("test-secret", ttl_minutes=60),
        AuditLogger(session_factory),
        access_ttl_minutes=60,
        refresh_ttl_days=30,
    )
