"""Audit logger — emits every recorded action to the structured log stream.

Persistence to the append-only ``audit_logs`` table lands in the next step; the
shape recorded here is already the final one, so wiring the repository in will not
touch a single call site.
"""

from __future__ import annotations

import structlog

from pharmacy_os.core.audit.entry import AuditEntry

_log = structlog.get_logger("audit")


class AuditLogger:
    def record(self, entry: AuditEntry) -> None:
        _log.info(
            "audit",
            audit_id=str(entry.id),
            tenant_id=str(entry.tenant_id),
            actor_user_id=str(entry.actor_user_id) if entry.actor_user_id else None,
            action=entry.action.value,
            target_type=entry.target_type,
            target_id=entry.target_id,
            occurred_at=entry.occurred_at.isoformat(),
            context=entry.context,
        )
