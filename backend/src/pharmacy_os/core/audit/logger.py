"""Minimal audit logger (Sprint 2).

For now audit entries are emitted to the structured log stream. Sprint 7
persists them to the append-only ``audit_logs`` table (see docs/03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog

from pharmacy_os.core.context import RequestContext

_log = structlog.get_logger("audit")


@dataclass(frozen=True, slots=True)
class AuditEntry:
    actor_id: UUID
    tenant_id: UUID
    action: str
    entity_type: str
    entity_id: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None


class AuditLogger:
    def record(self, entry: AuditEntry) -> None:
        _log.info(
            "audit",
            actor_id=str(entry.actor_id),
            tenant_id=str(entry.tenant_id),
            action=entry.action,
            entity_type=entry.entity_type,
            entity_id=entry.entity_id,
            before=entry.before,
            after=entry.after,
        )

    def record_action(
        self, context: RequestContext, action: str, entity_type: str, entity_id: str
    ) -> None:
        self.record(
            AuditEntry(
                actor_id=context.user_id,
                tenant_id=context.tenant_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
            )
        )
