"""Persistence port for the audit trail.

Deliberately **append + read only**: no ``update``, no ``delete``. A repository that
cannot rewrite history is the cheapest way to make the append-only rule structural
rather than a convention someone forgets.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from pharmacy_os.core.audit.entry import AuditAction, AuditEntry


class AuditLogRepository(Protocol):
    async def add(self, entry: AuditEntry) -> None: ...

    async def list(
        self,
        tenant_id: UUID,
        *,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        actor_user_id: UUID | None = None,
        action: AuditAction | None = None,
        target_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEntry]:
        """Newest first, scoped to one tenant. Filters are ANDed; ``None`` means
        "no constraint on this field". ``target_type`` filters by the kind of object
        acted on (e.g. ``"user"``, ``"Prescription"``) — the entity dimension the
        audit dashboard needs and the minimal ``/audit-logs`` query did not expose."""
        ...

    async def count(
        self,
        tenant_id: UUID,
        *,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
        actor_user_id: UUID | None = None,
        action: AuditAction | None = None,
        target_type: str | None = None,
    ) -> int:
        """Total matching rows, so a caller can page without guessing the end."""
        ...
