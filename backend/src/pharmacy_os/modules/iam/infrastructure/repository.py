"""SQLAlchemy implementations of the iam ports.

These repositories take no ``RequestContext``: authentication runs *before* a
context exists, so the tenant is either supplied explicitly by the caller or read
off the row itself. Callers in the application layer are responsible for checking
that a looked-up row belongs to the acting tenant — see ``IamService._user_or_404``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.modules.iam.domain import (
    ActivationStatus,
    BackupCode,
    Branch,
    RefreshSession,
    Role,
    RoleAssignment,
    Tenant,
    TwoFactorChallenge,
    User,
    UserTwoFactor,
    UyQuyenQuanTri,
)
from pharmacy_os.modules.iam.infrastructure.mappers import (
    assignment_to_domain,
    assignment_to_orm,
    backup_code_to_domain,
    backup_code_to_orm,
    branch_to_domain,
    branch_to_orm,
    challenge_to_domain,
    challenge_to_orm,
    role_to_domain,
    role_to_orm,
    session_to_domain,
    session_to_orm,
    tenant_to_domain,
    tenant_to_orm,
    two_factor_to_domain,
    two_factor_to_orm,
    user_to_domain,
    user_to_orm,
    uy_quyen_to_domain,
    uy_quyen_to_orm,
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
)


class SqlAlchemyTenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, tenant: Tenant) -> None:
        self._session.add(tenant_to_orm(tenant))
        await self._session.flush()

    async def get(self, tenant_id: UUID) -> Tenant | None:
        row = await self._session.get(TenantORM, tenant_id)
        return tenant_to_domain(row) if row is not None else None


class SqlAlchemyBranchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, branch: Branch) -> None:
        self._session.add(branch_to_orm(branch))
        await self._session.flush()

    async def get(self, branch_id: UUID) -> Branch | None:
        row = await self._session.get(BranchORM, branch_id)
        return branch_to_domain(row) if row is not None else None

    async def list_active(self, tenant_id: UUID) -> list[Branch]:
        """Ordered by ``code`` so ``/auth/login`` presents a stable branch list."""
        stmt = (
            select(BranchORM)
            .where(
                BranchORM.tenant_id == tenant_id,
                BranchORM.status == ActivationStatus.ACTIVE.value,
            )
            .order_by(BranchORM.code)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [branch_to_domain(r) for r in rows]


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(user_to_orm(user))
        await self._session.flush()

    async def get(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserORM, user_id)
        return user_to_domain(row) if row is not None else None

    async def find_by_email(self, email: str) -> User | None:
        stmt = select(UserORM).where(UserORM.email == email.strip().lower())
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return user_to_domain(row) if row is not None else None

    async def list(self, tenant_id: UUID, *, limit: int = 50, offset: int = 0) -> list[User]:
        stmt = (
            select(UserORM)
            .where(UserORM.tenant_id == tenant_id)
            .order_by(UserORM.email)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [user_to_domain(r) for r in rows]

    async def update(self, user: User) -> None:
        row = await self._session.get(UserORM, user.id)
        if row is None:
            return
        row.email = user.email
        row.password_hash = user.password_hash
        row.full_name = user.full_name
        row.status = user.status.value
        row.must_change_password = user.must_change_password
        row.failed_login_count = user.failed_login_count
        row.locked_until = user.locked_until
        row.last_login_at = user.last_login_at
        await self._session.flush()

    async def count(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).select_from(UserORM).where(UserORM.tenant_id == tenant_id)
        return int((await self._session.execute(stmt)).scalar_one())


class SqlAlchemyRoleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, role: Role) -> None:
        self._session.add(role_to_orm(role))
        await self._session.flush()

    async def get(self, role_id: UUID) -> Role | None:
        row = await self._session.get(RoleORM, role_id)
        return role_to_domain(row) if row is not None else None

    async def find_by_code(self, code: str, tenant_id: UUID | None = None) -> Role | None:
        stmt = select(RoleORM).where(
            RoleORM.code == code,
            RoleORM.tenant_id.is_(None) if tenant_id is None else RoleORM.tenant_id == tenant_id,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return role_to_domain(row) if row is not None else None

    async def list_available(self, tenant_id: UUID) -> list[Role]:
        stmt = (
            select(RoleORM)
            .where(or_(RoleORM.tenant_id.is_(None), RoleORM.tenant_id == tenant_id))
            .order_by(RoleORM.code)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [role_to_domain(r) for r in rows]

    async def update(self, role: Role) -> None:
        """Replace the role's permission rows wholesale.

        Permissions are a set, not an ordered history, so a delete-then-insert is
        both simplest and correct; the join table has no other columns to preserve.
        """
        row = await self._session.get(RoleORM, role.id)
        if row is None:
            return
        row.name = role.name
        row.description = role.description
        await self._session.execute(
            delete(RolePermissionORM).where(RolePermissionORM.role_id == role.id)
        )
        for permission in sorted(role.permissions):
            self._session.add(RolePermissionORM(role_id=role.id, permission=permission))
        await self._session.flush()
        await self._session.refresh(row)


class SqlAlchemyRoleAssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, assignment: RoleAssignment) -> None:
        self._session.add(assignment_to_orm(assignment))
        await self._session.flush()

    async def list_for_user(self, user_id: UUID) -> list[RoleAssignment]:
        stmt = select(UserRoleORM).where(UserRoleORM.user_id == user_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [assignment_to_domain(r) for r in rows]

    async def get(self, assignment_id: UUID) -> RoleAssignment | None:
        row = await self._session.get(UserRoleORM, assignment_id)
        return assignment_to_domain(row) if row is not None else None

    async def delete(self, assignment_id: UUID) -> None:
        await self._session.execute(delete(UserRoleORM).where(UserRoleORM.id == assignment_id))
        await self._session.flush()


class SqlAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, session: RefreshSession) -> None:
        self._session.add(session_to_orm(session))
        await self._session.flush()

    async def find_by_hash(self, token_hash: str) -> RefreshSession | None:
        stmt = select(RefreshTokenORM).where(RefreshTokenORM.token_hash == token_hash)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return session_to_domain(row) if row is not None else None

    async def update(self, session: RefreshSession) -> None:
        row = await self._session.get(RefreshTokenORM, session.id)
        if row is None:
            return
        row.revoked_at = session.revoked_at
        row.replaced_by = session.replaced_by
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> int:
        stmt = (
            update(RefreshTokenORM)
            .where(RefreshTokenORM.user_id == user_id, RefreshTokenORM.revoked_at.is_(None))
            .values(revoked_at=revoked_at)
        )
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        await self._session.flush()
        return result.rowcount

    async def delete_expired(self, now: datetime) -> int:
        stmt = delete(RefreshTokenORM).where(RefreshTokenORM.expires_at < now)
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        return result.rowcount


class SqlAlchemyUserTwoFactorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, config: UserTwoFactor) -> None:
        self._session.add(two_factor_to_orm(config))
        await self._session.flush()

    async def find_for_user(self, user_id: UUID) -> UserTwoFactor | None:
        stmt = select(UserTwoFactorORM).where(UserTwoFactorORM.user_id == user_id)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return two_factor_to_domain(row) if row is not None else None

    async def update(self, config: UserTwoFactor) -> None:
        row = await self._session.get(UserTwoFactorORM, config.id)
        if row is None:
            return
        row.secret = config.secret
        row.status = config.status.value
        row.confirmed_at = config.confirmed_at
        row.last_used_timestep = config.last_used_timestep
        await self._session.flush()

    async def delete_for_user(self, user_id: UUID) -> None:
        """Delete the configuration; backup codes go with it via ``ON DELETE CASCADE``.

        Deleting rather than flagging is the point: a disabled configuration that kept
        its secret would leave a live credential in the database for no purpose.
        """
        await self._session.execute(
            delete(UserTwoFactorORM).where(UserTwoFactorORM.user_id == user_id)
        )
        await self._session.flush()


class SqlAlchemyBackupCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def replace_all(self, two_factor_id: UUID, codes: list[BackupCode]) -> None:
        await self._session.execute(
            delete(TwoFactorBackupCodeORM).where(
                TwoFactorBackupCodeORM.two_factor_id == two_factor_id
            )
        )
        for code in codes:
            self._session.add(backup_code_to_orm(code))
        await self._session.flush()

    async def list_for(self, two_factor_id: UUID) -> list[BackupCode]:
        stmt = select(TwoFactorBackupCodeORM).where(
            TwoFactorBackupCodeORM.two_factor_id == two_factor_id
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [backup_code_to_domain(r) for r in rows]

    async def update(self, code: BackupCode) -> None:
        row = await self._session.get(TwoFactorBackupCodeORM, code.id)
        if row is None:
            return
        row.used_at = code.used_at
        await self._session.flush()


class SqlAlchemyTwoFactorChallengeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, challenge: TwoFactorChallenge) -> None:
        self._session.add(challenge_to_orm(challenge))
        await self._session.flush()

    async def find_by_hash(self, token_hash: str) -> TwoFactorChallenge | None:
        stmt = select(TwoFactorChallengeORM).where(TwoFactorChallengeORM.token_hash == token_hash)
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return challenge_to_domain(row) if row is not None else None

    async def update(self, challenge: TwoFactorChallenge) -> None:
        row = await self._session.get(TwoFactorChallengeORM, challenge.id)
        if row is None:
            return
        row.attempts = challenge.attempts
        row.consumed_at = challenge.consumed_at
        await self._session.flush()

    async def delete_expired(self, now: datetime) -> int:
        stmt = delete(TwoFactorChallengeORM).where(TwoFactorChallengeORM.expires_at < now)
        result = cast("CursorResult[Any]", await self._session.execute(stmt))
        return result.rowcount


class SqlAlchemyUyQuyenRepository:
    """Uỷ quyền quản trị — **chỉ ghi thêm**, không có ``delete_expired``.

    Xem :class:`~pharmacy_os.modules.iam.domain.ports.UyQuyenRepository`: hàng hết hạn
    là vết kiểm toán, không phải rác. Thu hồi là **ghi một mốc thời gian**, không phải
    một lượt ``DELETE`` — sổ phải còn đọc được rằng quyền ấy từng được cấp rồi bị rút.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, uy_quyen: UyQuyenQuanTri) -> None:
        self._session.add(uy_quyen_to_orm(uy_quyen))
        await self._session.flush()

    async def get(self, uy_quyen_id: UUID) -> UyQuyenQuanTri | None:
        row = await self._session.get(UyQuyenQuanTriORM, uy_quyen_id)
        return uy_quyen_to_domain(row) if row is not None else None

    async def list_con_hieu_luc(
        self, nguoi_nhan_id: UUID, bay_gio: datetime
    ) -> list[UyQuyenQuanTri]:
        # Lọc ở CSDL, không đọc hết rồi lọc trong Python: bảng chỉ-ghi-thêm nên phần
        # lịch sử tăng mãi, còn phần còn hiệu lực gần như luôn rỗng. Hai điều kiện này
        # là bản dịch SQL của ``UyQuyenQuanTri.con_hieu_luc`` — đổi một bên phải đổi
        # bên kia (test ``test_loc_sql_khop_luat_domain`` canh đúng chỗ này).
        stmt = (
            select(UyQuyenQuanTriORM)
            .where(
                UyQuyenQuanTriORM.nguoi_nhan_id == nguoi_nhan_id,
                UyQuyenQuanTriORM.thu_hoi_luc.is_(None),
                UyQuyenQuanTriORM.het_han_luc > bay_gio,
            )
            .order_by(UyQuyenQuanTriORM.cap_luc.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [uy_quyen_to_domain(row) for row in rows]

    async def list_cua_tenant(
        self, tenant_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[UyQuyenQuanTri]:
        stmt = (
            select(UyQuyenQuanTriORM)
            .where(UyQuyenQuanTriORM.tenant_id == tenant_id)
            .order_by(UyQuyenQuanTriORM.cap_luc.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [uy_quyen_to_domain(row) for row in rows]

    async def thu_hoi(self, uy_quyen_id: UUID, thu_hoi_luc: datetime) -> None:
        row = await self._session.get(UyQuyenQuanTriORM, uy_quyen_id)
        if row is None:
            return
        if row.thu_hoi_luc is not None:
            # Thu hồi lần hai không được đẩy mốc về sau: thời điểm quyền thật sự ngừng
            # có hiệu lực là lần **đầu**, và đó là con số sổ kiểm toán cần.
            return
        row.thu_hoi_luc = thu_hoi_luc
        await self._session.flush()
