import pytest
from pydantic import SecretStr

from pharmacy_os.core.config import (
    AppSettings,
    EncryptionSettings,
    OutboxSettings,
    SecuritySettings,
    Settings,
)

_PROD_SECRET = SecretStr("k" * 32)
"""Khoá ký đủ dài cho prod (≥32 byte, A-02).

Trước 2026-07-27 các test dưới dùng ``SecretStr("real")`` — **4 byte** — và prod
khởi động được. Đó chính là lỗ hổng kiểm toán nêu, nên khi cổng A-02 đóng lại thì
hai test kia đỏ. Chúng đỏ **đúng**: chúng đang khẳng định một hợp đồng không còn
tồn tại. Sửa test cho khớp cổng, không nới cổng cho khớp test."""

_PROD_ENCRYPTION = EncryptionSettings(enabled=False, allow_plaintext_in_prod=True)
"""Khai báo tường minh "prod này chưa mã hoá" (A-03).

Các test ở đây nói về *outbox* và *secret*, không nói về mã hoá — nên chúng đi qua
cổng A-03 bằng đường khai báo, đúng cách một deployment đang backfill dở sẽ làm.
Cổng A-03 có test riêng ở ``test_prod_fail_fast.py``."""


def test_defaults_boot_in_dev() -> None:
    s = Settings(app=AppSettings(env="dev"))
    assert s.ai.model_reasoning == "claude-opus-4-8"
    assert s.security.jwt_ttl_minutes == 60
    # Dev/test shape: events are published in-line, no background timers at all.
    assert s.outbox.sync_drain is True
    assert s.outbox.relay_enabled is False
    assert s.outbox.retention_enabled is False
    # Dead letters are never aged out on a timer — that needs a human's decision.
    assert s.outbox.retention_failed_days is None
    assert s.outbox.retention_published_days == 30


def test_prod_rejects_placeholder_secrets() -> None:
    with pytest.raises(ValueError):
        Settings(app=AppSettings(env="prod"))


def test_prod_boots_with_secrets() -> None:
    s = Settings(
        app=AppSettings(env="prod"),
        security=SecuritySettings(jwt_secret=_PROD_SECRET),
        ai={"api_key": SecretStr("real")},  # type: ignore[arg-type]
        encryption=_PROD_ENCRYPTION,
    )
    assert s.app.env == "prod"


def test_prod_rejects_an_outbox_with_no_delivery_path() -> None:
    """Both switches off means events pile up in ``event_outbox`` forever — refuse."""
    with pytest.raises(ValueError, match="event_outbox"):
        Settings(
            app=AppSettings(env="prod"),
            security=SecuritySettings(jwt_secret=_PROD_SECRET),
            ai={"api_key": SecretStr("real")},  # type: ignore[arg-type]
            outbox=OutboxSettings(sync_drain=False, relay_enabled=False),
            encryption=_PROD_ENCRYPTION,
        )


def test_prod_accepts_the_async_relay_shape() -> None:
    s = Settings(
        app=AppSettings(env="prod"),
        security=SecuritySettings(jwt_secret=_PROD_SECRET),
        ai={"api_key": SecretStr("real")},  # type: ignore[arg-type]
        outbox=OutboxSettings(sync_drain=False, relay_enabled=True),
        encryption=_PROD_ENCRYPTION,
    )
    assert s.outbox.relay_enabled is True
