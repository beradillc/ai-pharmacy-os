"""Mapping between iam ORM rows and domain entities."""

from __future__ import annotations

from datetime import UTC, datetime

from pharmacy_os.modules.iam.domain import (
    ActivationStatus,
    BackupCode,
    Branch,
    RefreshSession,
    Role,
    RoleAssignment,
    Tenant,
    TwoFactorChallenge,
    TwoFactorStatus,
    User,
    UserTwoFactor,
    UyQuyenQuanTri,
)
from pharmacy_os.modules.iam.infrastructure.models import (
    BranchORM,
    RefreshTokenORM,
    RoleORM,
    RolePermissionORM,
    TenantORM,
    TwoFactorBackupCodeORM,
    TwoFactorChallengeORM,
    UserORM,
    UserRoleORM,
    UserTwoFactorORM,
    UyQuyenQuanTriORM,
    UyQuyenQuyenORM,
)


def _as_utc(value: datetime | None) -> datetime | None:
    """Re-attach UTC to a timestamp read back from the database.

    ``DateTime(timezone=True)`` is honoured by Postgres but dropped by SQLite (the
    test harness), so values would come back naive there and blow up the ``now``
    comparisons in lockout and session-expiry checks. Everything is written in UTC,
    so re-attaching it is a restatement, not a conversion.
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


def tenant_to_domain(row: TenantORM) -> Tenant:
    return Tenant(id=row.id, name=row.name, status=ActivationStatus(row.status))


def tenant_to_orm(tenant: Tenant) -> TenantORM:
    return TenantORM(id=tenant.id, name=tenant.name, status=tenant.status.value)


def branch_to_domain(row: BranchORM) -> Branch:
    return Branch(
        id=row.id,
        tenant_id=row.tenant_id,
        code=row.code,
        name=row.name,
        status=ActivationStatus(row.status),
    )


def branch_to_orm(branch: Branch) -> BranchORM:
    return BranchORM(
        id=branch.id,
        tenant_id=branch.tenant_id,
        code=branch.code,
        name=branch.name,
        status=branch.status.value,
    )


def user_to_domain(row: UserORM) -> User:
    return User(
        id=row.id,
        tenant_id=row.tenant_id,
        email=row.email,
        password_hash=row.password_hash,
        full_name=row.full_name,
        status=ActivationStatus(row.status),
        must_change_password=row.must_change_password,
        failed_login_count=row.failed_login_count,
        locked_until=_as_utc(row.locked_until),
        last_login_at=_as_utc(row.last_login_at),
    )


def user_to_orm(user: User) -> UserORM:
    return UserORM(
        id=user.id,
        tenant_id=user.tenant_id,
        email=user.email,
        password_hash=user.password_hash,
        full_name=user.full_name,
        status=user.status.value,
        must_change_password=user.must_change_password,
        failed_login_count=user.failed_login_count,
        locked_until=user.locked_until,
        last_login_at=user.last_login_at,
    )


def role_to_domain(row: RoleORM) -> Role:
    return Role(
        id=row.id,
        tenant_id=row.tenant_id,
        code=row.code,
        name=row.name,
        description=row.description,
        permissions=frozenset(p.permission for p in row.permissions),
    )


def role_to_orm(role: Role) -> RoleORM:
    return RoleORM(
        id=role.id,
        tenant_id=role.tenant_id,
        code=role.code,
        name=role.name,
        description=role.description,
        permissions=[
            RolePermissionORM(role_id=role.id, permission=p) for p in sorted(role.permissions)
        ],
    )


def assignment_to_domain(row: UserRoleORM) -> RoleAssignment:
    return RoleAssignment(
        id=row.id,
        user_id=row.user_id,
        tenant_id=row.tenant_id,
        role_id=row.role_id,
        branch_id=row.branch_id,
        granted_by=row.granted_by,
        granted_at=_as_utc(row.granted_at) or row.granted_at,
    )


def assignment_to_orm(assignment: RoleAssignment) -> UserRoleORM:
    return UserRoleORM(
        id=assignment.id,
        user_id=assignment.user_id,
        tenant_id=assignment.tenant_id,
        role_id=assignment.role_id,
        branch_id=assignment.branch_id,
        granted_by=assignment.granted_by,
        granted_at=assignment.granted_at,
    )


def session_to_domain(row: RefreshTokenORM) -> RefreshSession:
    return RefreshSession(
        id=row.id,
        user_id=row.user_id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        token_hash=row.token_hash,
        issued_at=_as_utc(row.issued_at) or row.issued_at,
        expires_at=_as_utc(row.expires_at) or row.expires_at,
        revoked_at=_as_utc(row.revoked_at),
        replaced_by=row.replaced_by,
    )


def session_to_orm(session: RefreshSession) -> RefreshTokenORM:
    return RefreshTokenORM(
        id=session.id,
        user_id=session.user_id,
        tenant_id=session.tenant_id,
        branch_id=session.branch_id,
        token_hash=session.token_hash,
        issued_at=session.issued_at,
        expires_at=session.expires_at,
        revoked_at=session.revoked_at,
        replaced_by=session.replaced_by,
    )


def two_factor_to_domain(row: UserTwoFactorORM) -> UserTwoFactor:
    return UserTwoFactor(
        id=row.id,
        user_id=row.user_id,
        tenant_id=row.tenant_id,
        secret=row.secret,
        status=TwoFactorStatus(row.status),
        confirmed_at=_as_utc(row.confirmed_at),
        last_used_timestep=row.last_used_timestep,
        created_at=_as_utc(row.created_at) or row.created_at,
    )


def two_factor_to_orm(config: UserTwoFactor) -> UserTwoFactorORM:
    return UserTwoFactorORM(
        id=config.id,
        user_id=config.user_id,
        tenant_id=config.tenant_id,
        secret=config.secret,
        status=config.status.value,
        confirmed_at=config.confirmed_at,
        last_used_timestep=config.last_used_timestep,
    )


def backup_code_to_domain(row: TwoFactorBackupCodeORM) -> BackupCode:
    return BackupCode(
        id=row.id,
        two_factor_id=row.two_factor_id,
        code_hash=row.code_hash,
        used_at=_as_utc(row.used_at),
    )


def backup_code_to_orm(code: BackupCode) -> TwoFactorBackupCodeORM:
    return TwoFactorBackupCodeORM(
        id=code.id,
        two_factor_id=code.two_factor_id,
        code_hash=code.code_hash,
        used_at=code.used_at,
    )


def uy_quyen_to_domain(row: UyQuyenQuanTriORM) -> UyQuyenQuanTri:
    return UyQuyenQuanTri(
        id=row.id,
        tenant_id=row.tenant_id,
        nguoi_nhan_id=row.nguoi_nhan_id,
        nguoi_cap_id=row.nguoi_cap_id,
        ly_do=row.ly_do,
        quyen=frozenset(q.permission for q in row.quyen),
        cap_luc=_as_utc(row.cap_luc) or row.cap_luc,
        het_han_luc=_as_utc(row.het_han_luc) or row.het_han_luc,
        thu_hoi_luc=_as_utc(row.thu_hoi_luc),
    )


def uy_quyen_to_orm(uy_quyen: UyQuyenQuanTri) -> UyQuyenQuanTriORM:
    return UyQuyenQuanTriORM(
        id=uy_quyen.id,
        tenant_id=uy_quyen.tenant_id,
        nguoi_nhan_id=uy_quyen.nguoi_nhan_id,
        nguoi_cap_id=uy_quyen.nguoi_cap_id,
        ly_do=uy_quyen.ly_do,
        cap_luc=uy_quyen.cap_luc,
        het_han_luc=uy_quyen.het_han_luc,
        thu_hoi_luc=uy_quyen.thu_hoi_luc,
        quyen=[
            UyQuyenQuyenORM(uy_quyen_id=uy_quyen.id, permission=ma) for ma in sorted(uy_quyen.quyen)
        ],
    )


def challenge_to_domain(row: TwoFactorChallengeORM) -> TwoFactorChallenge:
    return TwoFactorChallenge(
        id=row.id,
        user_id=row.user_id,
        tenant_id=row.tenant_id,
        branch_id=row.branch_id,
        token_hash=row.token_hash,
        attempts=row.attempts,
        created_at=_as_utc(row.created_at) or row.created_at,
        expires_at=_as_utc(row.expires_at) or row.expires_at,
        consumed_at=_as_utc(row.consumed_at),
    )


def challenge_to_orm(challenge: TwoFactorChallenge) -> TwoFactorChallengeORM:
    return TwoFactorChallengeORM(
        id=challenge.id,
        user_id=challenge.user_id,
        tenant_id=challenge.tenant_id,
        branch_id=challenge.branch_id,
        token_hash=challenge.token_hash,
        attempts=challenge.attempts,
        created_at=challenge.created_at,
        expires_at=challenge.expires_at,
        consumed_at=challenge.consumed_at,
    )
