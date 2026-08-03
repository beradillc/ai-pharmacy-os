"""IAM persistence ports (implemented by infrastructure).

Unlike the other modules' repositories these are **not** tenant-scoped by a
``RequestContext``: login happens before any context exists, so lookups take the
tenant explicitly (or, for :meth:`UserRepository.find_by_email`, resolve it).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from pharmacy_os.modules.iam.domain.delegation import UyQuyenQuanTri
from pharmacy_os.modules.iam.domain.entities import (
    Branch,
    RefreshSession,
    Role,
    RoleAssignment,
    Tenant,
    User,
)
from pharmacy_os.modules.iam.domain.two_factor import (
    BackupCode,
    TwoFactorChallenge,
    UserTwoFactor,
)


class TenantRepository(Protocol):
    async def add(self, tenant: Tenant) -> None: ...

    async def get(self, tenant_id: UUID) -> Tenant | None: ...


class BranchRepository(Protocol):
    async def add(self, branch: Branch) -> None: ...

    async def get(self, branch_id: UUID) -> Branch | None: ...

    async def list_active(self, tenant_id: UUID) -> list[Branch]: ...


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get(self, user_id: UUID) -> User | None: ...

    async def find_by_email(self, email: str) -> User | None:
        """Look a user up across tenants — emails are globally unique (docs/15 D4)."""
        ...

    async def list(self, tenant_id: UUID, *, limit: int = 50, offset: int = 0) -> list[User]: ...

    async def update(self, user: User) -> None: ...

    async def count(self, tenant_id: UUID) -> int:
        """Used by tenant bootstrap to refuse re-seeding a populated tenant."""
        ...


class RoleRepository(Protocol):
    async def add(self, role: Role) -> None: ...

    async def get(self, role_id: UUID) -> Role | None: ...

    async def find_by_code(self, code: str, tenant_id: UUID | None = None) -> Role | None: ...

    async def list_available(self, tenant_id: UUID) -> list[Role]:
        """System roles plus the tenant's own roles."""
        ...

    async def update(self, role: Role) -> None: ...


class RoleAssignmentRepository(Protocol):
    async def add(self, assignment: RoleAssignment) -> None: ...

    async def list_for_user(self, user_id: UUID) -> list[RoleAssignment]: ...

    async def get(self, assignment_id: UUID) -> RoleAssignment | None: ...

    async def delete(self, assignment_id: UUID) -> None: ...


class RefreshTokenRepository(Protocol):
    async def add(self, session: RefreshSession) -> None: ...

    async def find_by_hash(self, token_hash: str) -> RefreshSession | None: ...

    async def update(self, session: RefreshSession) -> None: ...

    async def revoke_all_for_user(self, user_id: UUID, revoked_at: datetime) -> int:
        """Revoke every live session of a user; returns how many were revoked."""
        ...

    async def delete_expired(self, now: datetime) -> int:
        """Housekeeping: drop rows past ``expires_at`` (called on each refresh)."""
        ...


class UserTwoFactorRepository(Protocol):
    """One row per user at most — the absence of a row *is* "2FA disabled"."""

    async def add(self, config: UserTwoFactor) -> None: ...

    async def find_for_user(self, user_id: UUID) -> UserTwoFactor | None: ...

    async def update(self, config: UserTwoFactor) -> None: ...

    async def delete_for_user(self, user_id: UUID) -> None:
        """Remove the configuration and its backup codes (self-disable / admin reset)."""
        ...


class BackupCodeRepository(Protocol):
    async def replace_all(self, two_factor_id: UUID, codes: list[BackupCode]) -> None:
        """Issue a fresh set, discarding any previous one.

        Regenerating always invalidates the old sheet: a user who asks for new codes
        is telling you the old ones are no longer trustworthy.
        """
        ...

    async def list_for(self, two_factor_id: UUID) -> list[BackupCode]: ...

    async def update(self, code: BackupCode) -> None: ...


class UyQuyenRepository(Protocol):
    """Uỷ quyền quản trị có thời hạn (Chain chốt 2026-08-03).

    🔴 **Không có ``delete_expired`` như hai port trên.** Uỷ quyền hết hạn là **vết kiểm
    toán**, không phải rác dọn được: câu hỏi *"ai đã mở quyền đọc hồ sơ bệnh nhân cho ai,
    lúc nào, vì lý do gì"* chỉ trả lời được nếu hàng đã hết hạn vẫn nằm đó. Hết hiệu lực
    là một **phép so thời gian** (:meth:`UyQuyenQuanTri.con_hieu_luc`), không phải một
    lượt ``DELETE``.
    """

    async def add(self, uy_quyen: UyQuyenQuanTri) -> None: ...

    async def get(self, uy_quyen_id: UUID) -> UyQuyenQuanTri | None: ...

    async def list_con_hieu_luc(
        self, nguoi_nhan_id: UUID, bay_gio: datetime
    ) -> list[UyQuyenQuanTri]:
        """Uỷ quyền đang còn hiệu lực của một người — đường nóng, gọi mỗi request.

        Lọc ``thu_hoi_luc IS NULL AND het_han_luc > bay_gio`` **ở CSDL**, không đọc hết
        rồi lọc trong Python: bảng này chỉ-ghi-thêm, nên số hàng lịch sử tăng mãi trong
        khi số hàng còn hiệu lực gần như luôn là 0.
        """
        ...

    async def list_cua_tenant(
        self, tenant_id: UUID, *, limit: int = 50, offset: int = 0
    ) -> list[UyQuyenQuanTri]:
        """Cả lịch sử, mới nhất trước — màn rà soát của chủ chuỗi."""
        ...

    async def thu_hoi(self, uy_quyen_id: UUID, thu_hoi_luc: datetime) -> None: ...


class TwoFactorChallengeRepository(Protocol):
    async def add(self, challenge: TwoFactorChallenge) -> None: ...

    async def find_by_hash(self, token_hash: str) -> TwoFactorChallenge | None: ...

    async def update(self, challenge: TwoFactorChallenge) -> None: ...

    async def delete_expired(self, now: datetime) -> int:
        """Housekeeping, mirroring :meth:`RefreshTokenRepository.delete_expired`."""
        ...
