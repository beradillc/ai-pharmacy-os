"""Per-request execution context (tenant, branch, actor, permissions).

Carried explicitly through use-cases rather than pulled from globals, so the
domain stays testable. The API layer builds it from the JWT + ``X-Branch-Id``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RequestContext:
    tenant_id: UUID
    branch_id: UUID
    user_id: UUID
    permissions: frozenset[str] = field(default_factory=frozenset)

    def has(self, permission: str) -> bool:
        return permission in self.permissions
