"""Shared API dependencies: DI container access and request context.

NOTE (interim, Sprint 3): the full IAM module (users/roles/JWT issuance) lands
in Sprint 6. Until then, in non-production environments the context is
synthesised from ``X-Tenant-Id`` / ``X-Branch-Id`` / ``X-User-Id`` headers with a
development permission set. When an ``Authorization: Bearer`` token is present it
is always decoded for real permissions. Production refuses unauthenticated calls.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Request

from pharmacy_os.core.config import Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.di import Container
from pharmacy_os.core.errors import PermissionDeniedError
from pharmacy_os.core.security import JwtService

# Fixed development identities so balances persist across calls in a dev session.
_DEV_TENANT = UUID("00000000-0000-0000-0000-0000000a0001")
_DEV_BRANCH = UUID("00000000-0000-0000-0000-0000000b0001")
_DEV_USER = UUID("00000000-0000-0000-0000-0000000d0001")
_DEV_PERMISSIONS = frozenset(
    {
        "catalog.read",
        "catalog.create",
        "inventory.read",
        "inventory.receive",
        "inventory.dispense",
        "sales.read",
        "sales.create",
        "rx.read",
        "rx.create",
        "rx.approve",
        "rx.dispense",
        "clinical.check",
        "clinical.accept",
        "crm.create",
        "crm.read",
        "crm.write",
    }
)


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


def get_context(request: Request) -> RequestContext:
    container = get_container(request)
    settings = container.resolve(Settings)

    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        payload = container.resolve(JwtService).decode(auth[len("Bearer ") :])
        branch_header = request.headers.get("X-Branch-Id")
        return RequestContext(
            tenant_id=payload.tenant_id,
            branch_id=UUID(branch_header) if branch_header else payload.tenant_id,
            user_id=payload.user_id,
            permissions=payload.permissions,
        )

    if settings.app.env == "prod":
        raise PermissionDeniedError("Yêu cầu xác thực")

    return RequestContext(
        tenant_id=UUID(request.headers.get("X-Tenant-Id", str(_DEV_TENANT))),
        branch_id=UUID(request.headers.get("X-Branch-Id", str(_DEV_BRANCH))),
        user_id=UUID(request.headers.get("X-User-Id", str(_DEV_USER))),
        permissions=_DEV_PERMISSIONS,
    )
