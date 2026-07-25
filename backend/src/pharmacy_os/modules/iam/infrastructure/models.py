"""SQLAlchemy models for iam. Cross-dialect (Postgres + SQLite for tests).

Two conventions differ deliberately from the other modules:

1. **No ``TenantScopedMixin``.** It forces ``branch_id NOT NULL``, but a user
   belongs to a tenant and reaches branches through ``user_roles`` — where a NULL
   ``branch_id`` is the meaningful "chain-wide" value (docs/15 §0 F5).
2. **Foreign keys stay inside iam.** Business tables never FK to ``tenants``/
   ``branches``/``users``: their ``tenant_id``/``branch_id``/actor columns remain
   bare UUIDs, matching the existing convention (``sales.SaleLine.drug_id``,
   ``stock_reconciliation_needed.grn_id``) that keeps ``module-independence``
   holding at the schema level too.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pharmacy_os.core.db.base import Base, PkUuidMixin, TimestampMixin

_BRANCH_IS_NULL = text("branch_id IS NULL")
_BRANCH_IS_NOT_NULL = text("branch_id IS NOT NULL")
_TENANT_IS_NULL = text("tenant_id IS NULL")
_TENANT_IS_NOT_NULL = text("tenant_id IS NOT NULL")


class TenantORM(PkUuidMixin, TimestampMixin, Base):
    """One pharmacy business — the isolation boundary every other table scopes to."""

    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class BranchORM(PkUuidMixin, TimestampMixin, Base):
    """One outlet inside a tenant (nhà thuốc trong chuỗi)."""

    __tablename__ = "branches"
    __table_args__ = (Index("uq_branches_tenant_code", "tenant_id", "code", unique=True),)

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")


class UserORM(PkUuidMixin, TimestampMixin, Base):
    """A person who can sign in. ``email`` is unique across the whole deployment
    (docs/15 D4) so ``/auth/login`` needs no tenant selector.
    """

    __tablename__ = "users"

    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="ACTIVE")
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RoleORM(PkUuidMixin, TimestampMixin, Base):
    """``tenant_id IS NULL`` marks a system role shared by every tenant."""

    __tablename__ = "roles"
    __table_args__ = (
        # Same NULL-distinctness caveat as ``user_roles``: system roles (tenant_id
        # NULL) need their own partial index or ``UNIQUE(tenant_id, code)`` would
        # let ``cashier`` be seeded twice.
        Index(
            "uq_roles_system_code",
            "code",
            unique=True,
            postgresql_where=_TENANT_IS_NULL,
            sqlite_where=_TENANT_IS_NULL,
        ),
        Index(
            "uq_roles_tenant_code",
            "tenant_id",
            "code",
            unique=True,
            postgresql_where=_TENANT_IS_NOT_NULL,
            sqlite_where=_TENANT_IS_NOT_NULL,
        ),
    )

    tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenants.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    permissions: Mapped[list[RolePermissionORM]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RolePermissionORM(Base):
    """One permission code granted by a role — a plain join table, no surrogate id."""

    __tablename__ = "role_permissions"

    role_id: Mapped[UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission: Mapped[str] = mapped_column(String(64), primary_key=True)

    role: Mapped[RoleORM] = relationship(back_populates="permissions")


class UserRoleORM(PkUuidMixin, Base):
    """Grant of a role to a user, chain-wide (``branch_id IS NULL``) or per branch.

    The two partial unique indexes are **not** interchangeable with a single
    ``UNIQUE(user_id, role_id, branch_id)``: Postgres treats every NULL as distinct,
    so that constraint would happily accept duplicate chain-wide grants (docs/15 §3).
    """

    __tablename__ = "user_roles"
    __table_args__ = (
        Index(
            "uq_user_role_chain",
            "user_id",
            "role_id",
            unique=True,
            postgresql_where=_BRANCH_IS_NULL,
            sqlite_where=_BRANCH_IS_NULL,
        ),
        Index(
            "uq_user_role_branch",
            "user_id",
            "role_id",
            "branch_id",
            unique=True,
            postgresql_where=_BRANCH_IS_NOT_NULL,
            sqlite_where=_BRANCH_IS_NOT_NULL,
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(ForeignKey("tenants.id"), index=True, nullable=False)
    role_id: Mapped[UUID] = mapped_column(ForeignKey("roles.id"), index=True, nullable=False)
    branch_id: Mapped[UUID | None] = mapped_column(ForeignKey("branches.id"), index=True)
    granted_by: Mapped[UUID | None] = mapped_column()
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RefreshTokenORM(PkUuidMixin, Base):
    """One issued refresh token, stored as a SHA-256 hash of the opaque secret.

    Rotation writes ``revoked_at``/``replaced_by`` rather than deleting, so a replay
    of an already-rotated token is detectable instead of merely "not found"
    (docs/15 §4). Rows past ``expires_at`` are swept on each successful refresh.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID] = mapped_column(nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by: Mapped[UUID | None] = mapped_column()


class UserTwoFactorORM(PkUuidMixin, TimestampMixin, Base):
    """One user's TOTP configuration — at most one row per user (Sprint 8).

    ``user_id`` is UNIQUE rather than the primary key so the row keeps a stable
    surrogate id for ``two_factor_backup_codes`` to hang off, matching every other
    table in this module.

    "2FA disabled" is the **absence of a row**: disabling deletes, so no stale secret
    is left behind for a later database leak to expose.
    """

    __tablename__ = "user_two_factor"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False, index=True)

    secret: Mapped[str] = mapped_column(String(64), nullable=False)
    """Base32 TOTP secret, 32 chars today (160 bits); 64 leaves room without a migration.

    # TODO(sprint8-1b): mã hóa at-rest cột này.
    Stored in cleartext deliberately — see ``iam.domain.two_factor.UserTwoFactor``
    for the full reasoning. Short version: there is no key management in this
    codebase yet, so encrypting with a key sitting in the same ``.env`` would be
    theatre; and a database-only leak still does not yield account takeover, because
    both login and signing also require the password.
    """

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_timestep: Mapped[int | None] = mapped_column(BigInteger)
    """Highest RFC 6238 counter already spent — makes each code single-use.

    ``BigInteger``: the counter is unix-seconds/30, which passes 2^31 in the year
    3038. Cheap now, unfixable later.
    """


class TwoFactorBackupCodeORM(Base):
    """One recovery code, stored as a SHA-256 hash; used rows are marked, not deleted."""

    __tablename__ = "two_factor_backup_codes"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    two_factor_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_two_factor.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TwoFactorChallengeORM(PkUuidMixin, Base):
    """A login that passed the password and still owes its second factor.

    Deliberately a table rather than a short-lived JWT: ``api.deps.get_context``
    accepts any token ``JwtService`` can decode, so a challenge JWT would work as a
    zero-permission access token — and ``/auth/change-password`` needs no permission,
    only the current password, which the holder just proved. That would let a stolen
    password change the password without ever clearing 2FA. An opaque row closes it,
    and carries the single-use flag and attempt counter a stateless token cannot.
    """

    __tablename__ = "two_factor_challenges"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    branch_id: Mapped[UUID | None] = mapped_column()
    """The branch requested at step 1, replayed at step 2 so permissions resolve for
    the same branch the user asked for."""

    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
