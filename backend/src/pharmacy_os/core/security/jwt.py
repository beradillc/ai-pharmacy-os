"""JWT access-token encoding/decoding."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from pharmacy_os.core.errors import PermissionDeniedError


@dataclass(frozen=True, slots=True)
class TokenPayload:
    user_id: UUID
    tenant_id: UUID
    permissions: frozenset[str]


class JwtService:
    def __init__(self, secret: str, *, algorithm: str = "HS256", ttl_minutes: int = 60) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(minutes=ttl_minutes)

    def issue(self, payload: TokenPayload) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": str(payload.user_id),
            "tenant": str(payload.tenant_id),
            "perms": sorted(payload.permissions),
            "iat": int(now.timestamp()),
            "exp": int((now + self._ttl).timestamp()),
        }
        return jwt.encode(claims, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> TokenPayload:
        try:
            claims = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.PyJWTError as exc:  # expired, bad signature, malformed
            raise PermissionDeniedError("Token không hợp lệ hoặc đã hết hạn") from exc
        return TokenPayload(
            user_id=UUID(claims["sub"]),
            tenant_id=UUID(claims["tenant"]),
            permissions=frozenset(claims.get("perms", [])),
        )
