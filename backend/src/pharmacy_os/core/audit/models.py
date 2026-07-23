"""SQLAlchemy model for the append-only audit trail.

Lives in ``core`` rather than a module because auditing is kernel infrastructure
(like ``core.db`` and ``core.security``), used by every module and owned by none.
It imports only ``core.db.base``, so the "core knows no business modules" contract
still holds.

``actor_user_id`` carries **no foreign key** to ``users`` on purpose. Two reasons:
an audit row must survive the deletion of anything it references — an audit trail
that can be erased by deleting a user is not a trail — and the audit table must not
become the one thing that couples core to iam's schema.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pharmacy_os.core.db.base import Base, PkUuidMixin

# jsonb on Postgres, plain JSON elsewhere (SQLite tests) — same choice as clinical.
_JSONB = JSON().with_variant(JSONB(), "postgresql")


class AuditLogORM(PkUuidMixin, Base):
    """One immutable audit fact.

    No ``TimestampMixin``: ``occurred_at`` is the only time that matters and it is
    supplied by the caller, whereas ``updated_at`` would imply rows change.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        # The two ways an inspection actually asks: "everything in this window" and
        # "everything this person did".
        Index("ix_audit_logs_tenant_occurred", "tenant_id", "occurred_at"),
        Index("ix_audit_logs_tenant_actor", "tenant_id", "actor_user_id"),
    )

    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    actor_user_id: Mapped[UUID | None] = mapped_column()
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    context: Mapped[dict[str, str]] = mapped_column(_JSONB, nullable=False, default=dict)
