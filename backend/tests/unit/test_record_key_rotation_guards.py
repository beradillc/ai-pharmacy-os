"""Cổng của `seeds.record_key_rotation` — phần làm nó khác một cuốn sổ tay.

Lệnh này ghi một khẳng định vào vết kiểm toán ("khoá đã xoay từ v1 sang v2"). Nếu nó
ghi được mà không kiểm chứng, nó biến một câu hỏi mở thành một câu trả lời SAI có dấu —
tệ hơn không có dòng nào. Bốn test dưới đây canh đúng bốn cách nó có thể nói dối.
"""

from __future__ import annotations

import pytest
from seeds.record_key_rotation import RotationNotProven, _check_against_live_config

from pharmacy_os.core.config import EncryptionSettings, Settings, get_settings

_KEY = "A" * 43 + "="  # 32 byte base64


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _settings_with(keys: dict[int, str], current: int) -> Settings:
    return Settings(
        encryption=EncryptionSettings(
            enabled=True,
            keys=keys,  # type: ignore[arg-type]
            current_version=current,
            blind_index_key=_KEY,  # type: ignore[arg-type]
        )
    )


def _use(monkeypatch: pytest.MonkeyPatch, keys: dict[int, str], current: int) -> None:
    settings = _settings_with(keys, current)
    monkeypatch.setattr("seeds.record_key_rotation.get_settings", lambda: settings)


def test_accepts_a_rotation_the_live_config_confirms(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, {1: _KEY, 2: _KEY}, current=2)
    _check_against_live_config(1, 2)  # không nổ


def test_refuses_when_current_version_does_not_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ghi vết TRƯỚC khi xoay = ghi một việc chưa xảy ra."""
    _use(monkeypatch, {1: _KEY, 2: _KEY}, current=1)
    with pytest.raises(RotationNotProven, match="CURRENT_VERSION"):
        _check_against_live_config(1, 2)


def test_refuses_when_the_old_key_is_already_gone(monkeypatch: pytest.MonkeyPatch) -> None:
    """Khoá cũ biến khỏi cấu hình trong khi còn dòng mang thẻ đó là SỰ CỐ, không phải
    chuyện để ghi nhận rồi đi tiếp."""
    _use(monkeypatch, {2: _KEY}, current=2)
    with pytest.raises(RotationNotProven, match="Thiếu khoá"):
        _check_against_live_config(1, 2)


def test_refuses_a_rotation_from_a_version_to_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    _use(monkeypatch, {1: _KEY}, current=1)
    with pytest.raises(RotationNotProven, match="không có lần xoay nào"):
        _check_against_live_config(1, 1)
