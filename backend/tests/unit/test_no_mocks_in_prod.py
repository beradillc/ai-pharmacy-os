"""Cổng giả không được phép chạy ở prod — A-07.

Kiểm toán 2026-07-26: ``MockLLMProvider`` và ``MockNationalDrugDbGateway`` nạp cả khi
``APP__ENV=prod``, không một dòng cảnh báo.

Điểm mấu chốt của phát hiện này: mock ở prod **không hỏng ồn ào — nó trả lời**. Cổng
lâm sàng giả trả về "không có tương tác thuốc" trông y như thật, và dược sĩ tin. Cổng
liên thông giả trả ACK, nên báo cáo QĐ1867 coi như đã gửi trong khi chưa đi đâu cả.
Cả hai đều là sai sót **im lặng**, loại đắt nhất.
"""

from __future__ import annotations

import pytest

from pharmacy_os.core.bootstrap import ALLOW_MOCKS_IN_PROD_ENV, refuse_mock_in_prod
from pharmacy_os.core.config import (
    AISettings,
    AppSettings,
    DatabaseSettings,
    EncryptionSettings,
    SecuritySettings,
    Settings,
)

_MOCK = "MockLLMProvider"
_FAKES = "AI lâm sàng"


def _settings(env: str) -> Settings:
    """Cấu hình hợp lệ ở **mọi cổng khác**, để test nói về đúng một thứ: mock.

    Prod nay có thêm hai cổng riêng (A-02 khoá ký ≥32 byte, A-03 mã hoá at-rest) — nếu
    để chúng đỏ ở đây thì test này sẽ xanh/đỏ vì lý do không phải điều nó khẳng định.
    """
    return Settings(
        app=AppSettings(env=env),  # type: ignore[arg-type]
        db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),
        ai=AISettings(api_key="khoa-ai"),  # type: ignore[arg-type]
        security=SecuritySettings(jwt_secret="k" * 32, allow_dev_auth=False),  # type: ignore[arg-type]
        encryption=EncryptionSettings(enabled=False, allow_plaintext_in_prod=True),
    )


def test_prod_refuses_to_boot_with_a_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ALLOW_MOCKS_IN_PROD_ENV, raising=False)
    with pytest.raises(RuntimeError, match=_MOCK):
        refuse_mock_in_prod(_settings("prod"), _MOCK, _FAKES)


def test_the_error_says_what_is_being_faked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Thông báo phải nói **giả cái gì**, không chỉ "có mock".

    Người đọc nó lúc 2 giờ sáng cần biết ngay là mình sắp cho chạy cái gì giả, chứ
    không phải đi tra tên lớp.
    """
    monkeypatch.delenv(ALLOW_MOCKS_IN_PROD_ENV, raising=False)
    with pytest.raises(RuntimeError, match=_FAKES):
        refuse_mock_in_prod(_settings("prod"), _MOCK, _FAKES)


@pytest.mark.parametrize("env", ["dev", "staging"])
def test_other_environments_are_untouched(env: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Chỉ prod bị chặn — dev/staging chạy mock là bình thường và cần thiết."""
    monkeypatch.delenv(ALLOW_MOCKS_IN_PROD_ENV, raising=False)
    refuse_mock_in_prod(_settings(env), _MOCK, _FAKES)


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes"])
def test_the_drill_escape_hatch_works(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Diễn tập vận hành (dựng prod-like không có nhà cung cấp thật) vẫn phải làm được."""
    monkeypatch.setenv(ALLOW_MOCKS_IN_PROD_ENV, value)
    refuse_mock_in_prod(_settings("prod"), _MOCK, _FAKES)


@pytest.mark.parametrize("value", ["", "0", "false", "no", "maybe"])
def test_anything_that_is_not_a_yes_still_blocks(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fail-closed: chỉ một tập "có" tường minh mới mở cổng, mọi thứ khác vẫn chặn."""
    monkeypatch.setenv(ALLOW_MOCKS_IN_PROD_ENV, value)
    with pytest.raises(RuntimeError):
        refuse_mock_in_prod(_settings("prod"), _MOCK, _FAKES)
