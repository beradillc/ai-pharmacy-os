"""Role-based access control helpers.

Permissions are string codes like ``sales.create`` (see docs/11_API_DESIGN.md).
:func:`require_permission` guards use-cases; the API layer additionally wires
it as a FastAPI dependency once modules exist.
"""

from __future__ import annotations

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import PermissionDeniedError


def require_permission(context: RequestContext, permission: str) -> None:
    """Raise :class:`PermissionDeniedError` unless the actor holds *permission*."""
    if not context.has(permission):
        raise PermissionDeniedError(f"Thiếu quyền: {permission}")
