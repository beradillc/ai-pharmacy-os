"""JWT access-token encoding/decoding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from pharmacy_os.core.errors import UnauthenticatedError


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Claims carried by an access token.

    ``branch_id`` is signed into the token rather than read from a request header:
    permissions are resolved for one specific branch at login, so letting the client
    name the branch afterwards would hand it every branch of the tenant (docs/15 §0
    F1). It stays optional so tokens issued before the iam module — and the dev-auth
    path — still decode.
    """

    user_id: UUID
    tenant_id: UUID
    permissions: frozenset[str]
    branch_id: UUID | None = None


class JwtService:
    def __init__(self, secret: str, *, algorithm: str = "HS256", ttl_minutes: int = 60) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(minutes=ttl_minutes)

    def issue(self, payload: TokenPayload) -> str:
        now = datetime.now(UTC)
        claims: dict[str, object] = {
            "sub": str(payload.user_id),
            "tenant": str(payload.tenant_id),
            "perms": sorted(payload.permissions),
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
        }
        if payload.branch_id is not None:
            claims["branch"] = str(payload.branch_id)
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> TokenPayload:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:  # expired, bad signature, malformed
            # 🔴 **401, KHÔNG phải 403** (V3-10, Chain nêu 2026-08-04).
            #
            # Bản trước ném ``PermissionDeniedError`` ⇒ 403 *"Không đủ quyền"*. Sai về ngữ
            # nghĩa, và cái sai ấy đi thẳng ra màn hình: người dùng **CÓ** quyền, chỉ là
            # **phiên đã hết**. ``UnauthenticatedError`` tự khai đúng ranh giới này ngay
            # trong docstring của nó — *"distinct from 403, which means known but not
            # allowed"*; chỗ này chỉ là dùng nhầm.
            #
            # Hệ quả ngoài đời Chain bắt được: màn báo *"Token không hợp lệ hoặc đã hết
            # hạn"* kèm nút **Thử lại** — mà thử lại là gửi lại đúng cái token đã chết,
            # không lần nào thành công được. Mã trạng thái đúng mới cho phép frontend phân
            # biệt *"đăng nhập lại"* với *"thử lại"*.
            raise UnauthenticatedError("Phiên đăng nhập đã hết, vui lòng đăng nhập lại") from exc
        branch = claims.get("branch")
        return TokenPayload(
            user_id=UUID(claims["sub"]),
            tenant_id=UUID(claims["tenant"]),
            permissions=frozenset(claims.get("perms", [])),
            branch_id=UUID(branch) if branch else None,
        )
