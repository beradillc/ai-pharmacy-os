"""Shared API dependencies: DI container access and request context.

The context comes from the ``Authorization: Bearer`` token and **only** from it.
Both the tenant and the branch are signed claims: permissions are resolved for one
specific branch when the token is issued (``iam.AuthService``), so honouring a
client-supplied ``X-Branch-Id`` on an authenticated request would hand the caller
every branch of the tenant with the permissions of the one they were granted. That
was the pre-iam behaviour and it is deliberately gone (docs/15 §0 F1/F2).

A development fallback that synthesises a context from ``X-Tenant-Id`` /
``X-Branch-Id`` / ``X-User-Id`` headers still exists for local work and the older
integration tests, but it is now **fail-closed**: it requires
``SECURITY__ALLOW_DEV_AUTH=true`` *and* a non-production environment, and
``Settings`` refuses to boot if production ever sets that flag.
"""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import Request

from pharmacy_os.core.config import Settings
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.di import Container
from pharmacy_os.core.errors import UnauthenticatedError
from pharmacy_os.core.http import client_ip_of
from pharmacy_os.core.security import JwtService
from pharmacy_os.core.security.branch_scope import BranchScopeGuard
from pharmacy_os.modules.iam.domain import ALL_PERMISSIONS

_log = structlog.get_logger("api.auth")

# Fixed development identities so balances persist across calls in a dev session.
_DEV_TENANT = UUID("00000000-0000-0000-0000-0000000a0001")
_DEV_BRANCH = UUID("00000000-0000-0000-0000-0000000b0001")
_DEV_USER = UUID("00000000-0000-0000-0000-0000000d0001")
_DEV_PERMISSIONS = ALL_PERMISSIONS
"""Every permission the codebase defines, taken from the iam role catalogue rather
than a hand-maintained copy — the previous literal had drifted to 26 of the 32 codes
actually used, silently making the compliance use-cases unreachable in dev
(docs/15 §0 F3)."""


def get_container(request: Request) -> Container:
    container: Container = request.app.state.container
    return container


async def get_context(request: Request) -> RequestContext:
    container = get_container(request)
    settings = container.resolve(Settings)

    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Bearer "):
        payload = container.resolve(JwtService).decode(auth[len("Bearer ") :])
        if payload.branch_id is None:
            # Only tokens minted before the iam module lack the claim; they cannot be
            # scoped to a branch, so they are no longer usable.
            raise UnauthenticatedError("Token thiếu thông tin chi nhánh, vui lòng đăng nhập lại")
        # Audit B-07: hai claim đều đã ký, nhưng chưa ai kiểm chúng có ĐI VỚI NHAU
        # không. Đường cấp token hôm nay không thể sinh ra cặp lệch — nhưng đó là tính
        # chất của một đường mã nguồn, không phải một ràng buộc. Kiểm ở đây biến nó
        # thành ràng buộc cho mọi đường vào, kể cả đường chưa được viết.
        guard = container.resolve(BranchScopeGuard)
        if not await guard.is_valid(payload.tenant_id, payload.branch_id):
            _log.warning(
                "branch_tenant_mismatch",
                tenant_id=str(payload.tenant_id),
                branch_id=str(payload.branch_id),
                user_id=str(payload.user_id),
                detail="token mang cặp tenant/chi nhánh không tồn tại — từ chối",
            )
            raise UnauthenticatedError("Token không hợp lệ, vui lòng đăng nhập lại")
        return RequestContext(
            tenant_id=payload.tenant_id,
            branch_id=payload.branch_id,
            user_id=payload.user_id,
            permissions=payload.permissions,
            client_ip=client_ip_of(request),
        )

    if not settings.security.allow_dev_auth:
        raise UnauthenticatedError("Yêu cầu xác thực")

    return RequestContext(
        tenant_id=UUID(request.headers.get("X-Tenant-Id", str(_DEV_TENANT))),
        branch_id=UUID(request.headers.get("X-Branch-Id", str(_DEV_BRANCH))),
        user_id=UUID(request.headers.get("X-User-Id", str(_DEV_USER))),
        permissions=_DEV_PERMISSIONS,
        client_ip=client_ip_of(request),
    )


def warn_if_dev_auth_enabled(settings: Settings) -> None:
    """Log loudly at startup when the header fallback is live."""
    if settings.security.allow_dev_auth:
        _log.warning(
            "dev_auth_enabled",
            detail=(
                "SECURITY__ALLOW_DEV_AUTH=true: requests without a Bearer token are "
                "accepted with full permissions. Never enable outside dev/test."
            ),
            env=settings.app.env,
        )
