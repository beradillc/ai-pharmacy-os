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
from pharmacy_os.core.http import client_ip_of, user_agent_of
from pharmacy_os.core.security import JwtService
from pharmacy_os.core.security.branch_scope import TokenScopeGuard
from pharmacy_os.core.security.uy_quyen_scope import UyQuyenGuard
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
        guard = container.resolve(TokenScopeGuard)
        branch_ok = await guard.branch_belongs_to_tenant(payload.tenant_id, payload.branch_id)
        user_ok = await guard.user_belongs_to_tenant(payload.tenant_id, payload.user_id)
        if not (branch_ok and user_ok):
            # Một dòng log, không phải hai: người vận hành cần biết "token này có claim
            # không đi với nhau", còn claim nào lệch là chi tiết để điều tra, không phải
            # hai sự kiện khác nhau.
            _log.warning(
                "token_scope_mismatch",
                tenant_id=str(payload.tenant_id),
                branch_id=str(payload.branch_id),
                user_id=str(payload.user_id),
                branch_ok=branch_ok,
                user_ok=user_ok,
                detail="claim trong token không đi được với nhau — từ chối (audit B-07/B-13)",
            )
            raise UnauthenticatedError("Token không hợp lệ, vui lòng đăng nhập lại")

        # Uỷ quyền quản trị có thời hạn (Chain chốt 2026-08-03): quyền MƯỢN được cộng vào
        # đây, ở tầng request — cố ý KHÔNG nằm trong token đã ký. Một uỷ quyền 24 giờ nằm
        # trong JWT sẽ sống dai hơn cửa sổ của chính nó (token cấp lúc 23:59 vẫn mang quyền
        # ấy sau khi uỷ quyền đã hết), tức cơ chế kiểm soát hỏng đúng ở chỗ nó tồn tại để
        # canh. Xem `core/security/uy_quyen_scope.py` và ràng buộc cài đặt #1 của
        # `docs/features/uy-quyen-quan-tri/01_DECISIONS.md`.
        muon = await container.resolve(UyQuyenGuard).quyen_duoc_uy_quyen(
            payload.tenant_id, payload.user_id
        )
        if muon:
            # Ghi log ở mức info, không phải warning: đây là một cơ chế hợp lệ đang hoạt
            # động đúng thiết kế, không phải một bất thường. Nhưng nó PHẢI để lại dòng —
            # "vì sao tài khoản này đọc được hồ sơ bệnh nhân lúc 2 giờ sáng" là câu hỏi
            # người rà soát sẽ hỏi, và câu trả lời không được chỉ nằm trong một bảng.
            _log.info(
                "quyen_uy_quyen_ap_dung",
                tenant_id=str(payload.tenant_id),
                user_id=str(payload.user_id),
                so_quyen_muon=len(muon),
                detail="quyền thêm từ uỷ quyền quản trị còn hiệu lực",
            )
        return RequestContext(
            tenant_id=payload.tenant_id,
            branch_id=payload.branch_id,
            user_id=payload.user_id,
            # Hợp NHẤT, không thay thế: uỷ quyền chỉ **thêm**, không bao giờ bớt. Một cơ chế
            # mở quyền mà lại có đường làm mất quyền là một cơ chế không ai dám bật.
            permissions=payload.permissions | muon,
            client_ip=client_ip_of(request),
            user_agent=user_agent_of(request),
        )

    if not settings.security.allow_dev_auth:
        raise UnauthenticatedError("Yêu cầu xác thực")

    return RequestContext(
        tenant_id=UUID(request.headers.get("X-Tenant-Id", str(_DEV_TENANT))),
        branch_id=UUID(request.headers.get("X-Branch-Id", str(_DEV_BRANCH))),
        user_id=UUID(request.headers.get("X-User-Id", str(_DEV_USER))),
        permissions=_DEV_PERMISSIONS,
        client_ip=client_ip_of(request),
        user_agent=user_agent_of(request),
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
