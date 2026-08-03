"""The bundle of iam repositories a use-case works with.

The other modules inject a single ``repo_factory(uow, ctx)``. IAM needs ten
repositories and — because authentication runs before any ``RequestContext``
exists — cannot bind them to a context, so they travel as one bundle built from
the unit of work instead of six separate factory parameters.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pharmacy_os.core.db import UnitOfWork
from pharmacy_os.modules.iam.domain import (
    BackupCodeRepository,
    BranchRepository,
    RefreshTokenRepository,
    RoleAssignmentRepository,
    RoleRepository,
    TenantRepository,
    TwoFactorChallengeRepository,
    UserRepository,
    UserTwoFactorRepository,
    UyQuyenRepository,
)


@dataclass(frozen=True, slots=True)
class IamRepositories:
    tenants: TenantRepository
    branches: BranchRepository
    users: UserRepository
    roles: RoleRepository
    assignments: RoleAssignmentRepository
    sessions: RefreshTokenRepository
    two_factor: UserTwoFactorRepository
    backup_codes: BackupCodeRepository
    challenges: TwoFactorChallengeRepository
    uy_quyen: UyQuyenRepository


UowFactory = Callable[[], UnitOfWork]
ReposFactory = Callable[[UnitOfWork], IamRepositories]
