"""SQLAlchemy model for the transactional outbox.

Lives in ``core`` rather than a module because the outbox is kernel infrastructure
(like ``core.db`` and ``core.audit``), written by every module's Unit of Work and
owned by none. It imports only ``core.db.base``, so the "core knows no business
modules" contract still holds.

The row carries **no foreign key** to anything it references: an outbox row must be
publishable long after — or independently of — whatever produced it, and it must not
couple core to any module's schema (same reasoning as ``audit_logs``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from pharmacy_os.core.db.base import Base, PkUuidMixin

# jsonb on Postgres, plain JSON elsewhere (SQLite tests) — same choice as audit/clinical.
_JSONB = JSON().with_variant(JSONB(), "postgresql")


class OutboxEventORM(PkUuidMixin, Base):
    """One recorded domain event awaiting at-least-once publication."""

    __tablename__ = "event_outbox"
    __table_args__ = (
        # The relay's hot query: "oldest PENDING rows that are due now". Ordering by
        # occurred_at is done separately; this index narrows to the claimable set.
        Index("ix_event_outbox_dispatch", "status", "next_attempt_at"),
        # Retention / per-tenant inspection.
        Index("ix_event_outbox_tenant_occurred", "tenant_id", "occurred_at"),
        # One row per event: re-collecting the same event (idempotent producer) or a
        # double-insert can never enqueue a duplicate delivery.
        UniqueConstraint("event_id", name="uq_event_outbox_event_id"),
    )

    event_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(_JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="PENDING")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
