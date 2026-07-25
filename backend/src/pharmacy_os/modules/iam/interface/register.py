"""Compose the iam module: build its services and routers.

Returns two routers rather than one: ``/auth`` is public (login runs before any
context exists) while ``/users`` and ``/roles`` are permission-guarded. Keeping them
separate makes that difference visible at the composition root instead of hiding it
inside per-endpoint dependencies.
"""

from __future__ import annotations

from fastapi import APIRouter

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import Settings
from pharmacy_os.core.db import UnitOfWork, UnitOfWorkFactory
from pharmacy_os.core.di import Container
from pharmacy_os.core.security import JwtService
from pharmacy_os.modules.iam.application import AuthService, IamRepositories, IamService
from pharmacy_os.modules.iam.infrastructure import (
    SqlAlchemyBackupCodeRepository,
    SqlAlchemyBranchRepository,
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyRoleAssignmentRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyTenantRepository,
    SqlAlchemyTwoFactorChallengeRepository,
    SqlAlchemyUserRepository,
    SqlAlchemyUserTwoFactorRepository,
)
from pharmacy_os.modules.iam.interface.router import (
    ContextDep,
    build_admin_router,
    build_auth_router,
)


def build_repositories(uow: UnitOfWork) -> IamRepositories:
    return IamRepositories(
        tenants=SqlAlchemyTenantRepository(uow.session),
        branches=SqlAlchemyBranchRepository(uow.session),
        users=SqlAlchemyUserRepository(uow.session),
        roles=SqlAlchemyRoleRepository(uow.session),
        assignments=SqlAlchemyRoleAssignmentRepository(uow.session),
        sessions=SqlAlchemyRefreshTokenRepository(uow.session),
        two_factor=SqlAlchemyUserTwoFactorRepository(uow.session),
        backup_codes=SqlAlchemyBackupCodeRepository(uow.session),
        challenges=SqlAlchemyTwoFactorChallengeRepository(uow.session),
    )


def register(container: Container, get_context: ContextDep) -> list[APIRouter]:
    settings = container.resolve(Settings)
    audit = container.resolve(AuditLogger)

    uow_factory = container.resolve(UnitOfWorkFactory)

    auth_service = AuthService(
        uow_factory,
        build_repositories,
        container.resolve(JwtService),
        audit,
        access_ttl_minutes=settings.security.jwt_ttl_minutes,
        refresh_ttl_days=settings.security.refresh_ttl_days,
        two_factor_enforced=settings.security.two_factor_enforced,
    )
    iam_service = IamService(uow_factory, build_repositories, audit, auth_service)
    container.register_instance(IamService, iam_service)
    container.register_instance(AuthService, auth_service)

    return [build_auth_router(get_context), build_admin_router(get_context)]
