"""Prod từ chối khởi động khi cấu hình an toàn còn hở — A-02 / A-03.

Kiểm toán 2026-07-26 khởi động được `APP__ENV=prod` với **JWT_SECRET 3 byte** và
với **mã hoá at-rest tắt**. Chain nâng cả hai thành 🚫 release blocker Sprint 9.

Cách kiểm ở đây cố ý là *dựng `Settings` thật rồi xem nó có nổ không*, không phải
đọc mã nguồn — cùng khuôn với tiền lệ đã có cho ``ALLOW_DEV_AUTH``. Một cổng an
toàn chỉ có giá trị khi có thứ chứng minh nó đóng được.
"""

from __future__ import annotations

import base64

import pytest

from pharmacy_os.core.config import (
    AISettings,
    AppSettings,
    DatabaseSettings,
    EncryptionSettings,
    SecuritySettings,
    Settings,
)

_LONG_ENOUGH = "k" * 32
_TOO_SHORT = "abc"

_A_KEY = base64.b64encode(b"k" * 32).decode("ascii")
"""Khoá AES-256 hợp lệ về hình dạng — test này nói về *cổng khởi động*, không về mã hoá."""


def _encryption_on() -> EncryptionSettings:
    return EncryptionSettings(
        enabled=True,
        keys={1: _A_KEY},  # type: ignore[dict-item]
        blind_index_key=_A_KEY,  # type: ignore[arg-type]
    )


def _prod(
    *,
    jwt_secret: str = _LONG_ENOUGH,
    encryption: EncryptionSettings | None = None,
) -> Settings:
    """Cấu hình prod hợp lệ ở mọi mặt khác, để test nói về đúng một biến."""
    return Settings(
        app=AppSettings(env="prod", debug=False),
        db=DatabaseSettings(url="postgresql+asyncpg://u:p@localhost:5432/x"),
        ai=AISettings(api_key="that-la-khoa-ai"),  # type: ignore[arg-type]
        security=SecuritySettings(jwt_secret=jwt_secret, allow_dev_auth=False),  # type: ignore[arg-type]
        encryption=encryption if encryption is not None else _encryption_on(),
    )


# --- A-02: độ dài khoá ký ---------------------------------------------------
def test_prod_refuses_a_short_jwt_secret() -> None:
    """Đúng con số kiểm toán tái hiện được: khoá 3 byte, prod vẫn chạy. Nay phải nổ."""
    with pytest.raises(ValueError, match="SECURITY__JWT_SECRET"):
        _prod(jwt_secret=_TOO_SHORT)


@pytest.mark.parametrize("length", [1, 16, 31])
def test_prod_refuses_every_secret_below_the_floor(length: int) -> None:
    """31 byte cũng bị từ chối — sàn là một ngưỡng, không phải một gợi ý."""
    with pytest.raises(ValueError, match="tối thiểu"):
        _prod(jwt_secret="x" * length)


def test_prod_accepts_a_secret_at_the_floor() -> None:
    """Và đúng 32 byte thì qua — cổng phải mở được, nếu không nó chỉ là cái tường."""
    assert _prod(jwt_secret="y" * 32).app.env == "prod"


def test_the_length_floor_is_measured_in_bytes_not_characters() -> None:
    """31 ký tự tiếng Việt có dấu **là** hơn 32 byte UTF-8 — và đó là điều đúng.

    HMAC ăn byte, không ăn ký tự. Test này giữ cho phép đo đứng ở đúng đơn vị:
    đếm bằng ``len(str)`` sẽ từ chối nhầm một khoá thật ra đã đủ mạnh.
    """
    secret = "à" * 17  # 34 byte UTF-8, 17 ký tự
    assert len(secret) < 32 < len(secret.encode("utf-8"))
    assert _prod(jwt_secret=secret).app.env == "prod"


def test_dev_is_left_alone() -> None:
    """Sàn chỉ áp ở prod. Máy dev không phải chỗ để cưỡng chế chuyện này."""
    assert (
        Settings(
            app=AppSettings(env="dev", debug=True),
            db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),
            security=SecuritySettings(jwt_secret=_TOO_SHORT),  # type: ignore[arg-type]
        ).app.env
        == "dev"
    )


# --- A-03: mã hoá at-rest ---------------------------------------------------
def test_prod_refuses_plaintext_storage_by_default() -> None:
    """Quên đặt biến ⇒ app không khởi động, KHÔNG phải ⇒ dữ liệu bệnh nhân để trần."""
    with pytest.raises(ValueError, match="ENCRYPTION__ENABLED"):
        _prod(encryption=EncryptionSettings(enabled=False))


def test_prod_allows_plaintext_only_when_declared_out_loud() -> None:
    """Có đường thoát cho deployment đang backfill dở — nhưng phải khai báo tường minh."""
    assert (
        _prod(
            encryption=EncryptionSettings(enabled=False, allow_plaintext_in_prod=True)
        ).encryption.enabled
        is False
    )
