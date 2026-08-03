"""IAM use-cases: authentication and user/role administration."""

from pharmacy_os.modules.iam.application.auth_service import AuthService, hash_refresh_token
from pharmacy_os.modules.iam.application.dto import (
    AssignRoleInput,
    BootstrapTenantInput,
    BootstrapTenantOutput,
    BranchOutput,
    ChangePasswordInput,
    CreateUserInput,
    LoginInput,
    RoleAssignmentOutput,
    RoleOutput,
    SessionOutput,
    StepUpResult,
    SystemRoleSyncOutput,
    TwoFactorActivationOutput,
    TwoFactorEnrollmentOutput,
    TwoFactorLoginInput,
    TwoFactorStatusOutput,
    UserOutput,
)
from pharmacy_os.modules.iam.application.errors import (
    BranchSelectionRequiredError,
    TwoFactorEnrollmentRequiredError,
    TwoFactorRequiredError,
)
from pharmacy_os.modules.iam.application.iam_service import IamService
from pharmacy_os.modules.iam.application.repositories import (
    IamRepositories,
    ReposFactory,
    UowFactory,
)
from pharmacy_os.modules.iam.application.uy_quyen_service import UyQuyenService

__all__ = [
    "AssignRoleInput",
    "AuthService",
    "BootstrapTenantInput",
    "BootstrapTenantOutput",
    "BranchOutput",
    "BranchSelectionRequiredError",
    "ChangePasswordInput",
    "CreateUserInput",
    "IamRepositories",
    "IamService",
    "LoginInput",
    "ReposFactory",
    "RoleAssignmentOutput",
    "RoleOutput",
    "SessionOutput",
    "StepUpResult",
    "SystemRoleSyncOutput",
    "TwoFactorActivationOutput",
    "TwoFactorEnrollmentOutput",
    "TwoFactorEnrollmentRequiredError",
    "TwoFactorLoginInput",
    "TwoFactorRequiredError",
    "TwoFactorStatusOutput",
    "UowFactory",
    "UserOutput",
    "UyQuyenService",
    "hash_refresh_token",
]
