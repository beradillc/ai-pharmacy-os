from uuid import uuid4

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import PermissionDeniedError
from pharmacy_os.core.security import (
    JwtService,
    TokenPayload,
    hash_password,
    require_permission,
    verify_password,
)


def test_password_round_trip() -> None:
    hashed = hash_password("s3cr3t")
    assert hashed != "s3cr3t"
    assert verify_password("s3cr3t", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_round_trip() -> None:
    svc = JwtService("test-secret-key-0123456789abcdef", ttl_minutes=5)
    payload = TokenPayload(
        user_id=uuid4(), tenant_id=uuid4(), permissions=frozenset({"sales.create"})
    )
    token = svc.issue(payload)
    decoded = svc.decode(token)
    assert decoded.user_id == payload.user_id
    assert "sales.create" in decoded.permissions


def test_jwt_bad_token_raises() -> None:
    with pytest.raises(PermissionDeniedError):
        JwtService("test-secret-key-0123456789abcdef").decode("not-a-token")


def test_require_permission() -> None:
    ctx = RequestContext(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
        permissions=frozenset({"sales.create"}),
    )
    require_permission(ctx, "sales.create")  # no raise
    with pytest.raises(PermissionDeniedError):
        require_permission(ctx, "rx.approve")
