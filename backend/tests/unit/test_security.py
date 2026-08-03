from uuid import uuid4

import pytest

from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import PermissionDeniedError, UnauthenticatedError
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


def test_jwt_bad_token_raises_401_KHONG_phai_403() -> None:
    """🔴 Kỳ vọng đổi CÓ CHỦ Ý 2026-08-04 (V3-10), không phải nới lỏng để cho xanh.

    Bản trước khẳng định token hỏng ném ``PermissionDeniedError`` ⇒ **403 "Không đủ quyền"**.
    Sai về ngữ nghĩa, và cái sai ấy đi thẳng ra màn hình: người dùng **CÓ** quyền, chỉ là
    **phiên đã hết**. Chính ``UnauthenticatedError`` khai đúng ranh giới ấy trong docstring
    của nó — *"distinct from 403, which means known but not allowed"*.

    Ca thật Chain bắt được: màn báo *"Token không hợp lệ hoặc đã hết hạn"* kèm nút **Thử
    lại** — mà thử lại là gửi lại đúng token đã chết. Mã trạng thái đúng mới cho phép
    frontend phân biệt *"đăng nhập lại"* với *"thử lại"*.

    Khẳng định thêm **mã trạng thái**, không chỉ loại ngoại lệ: loại ngoại lệ là chi tiết cài
    đặt, còn thứ đi ra tới người dùng và tới frontend là **con số 401**.
    """
    with pytest.raises(UnauthenticatedError) as loi:
        JwtService("test-secret-key-0123456789abcdef").decode("not-a-token")
    assert loi.value.status_code == 401


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
