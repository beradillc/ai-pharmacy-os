"""Canh khoảng mù mà phần tăng tốc bcrypt tạo ra.

``tests/conftest.py`` hạ chi phí bcrypt xuống ``rounds=4`` cho cả bộ test (132,5 s
tiết kiệm được, 46,6 % của ``tests/integration``). Cái giá: **mọi test khác nay chạy
trên mức băm rẻ**, nên nếu ai đó ghim một chi phí thấp vào chính mã sản phẩm, chúng
sẽ không nhận ra.

File này là chỗ duy nhất trong bộ test khôi phục lại ``bcrypt.gensalt`` **thật** và
hỏi thẳng: *mã sản phẩm băm mật khẩu với chi phí bao nhiêu?* Không có nó, khoản tiết
kiệm 132 giây được đổi bằng một khoảng mù không ai canh — mà "khoảng mù không ai
canh" đúng là hình dạng chung của 16 sự cố *niềm tin giả* trong kiểm toán 2026-07-26.
Đây là điều kiện GĐ đặt ra khi duyệt việc hạ chi phí (2026-07-27).

**Xoá tăng tốc thì xoá luôn file này. Xoá file này mà giữ tăng tốc là mở lại đúng
khoảng mù vừa bịt.**
"""

from __future__ import annotations

import bcrypt
import pytest

from pharmacy_os.core.security.password import hash_password, verify_password
from tests.conftest import TEST_BCRYPT_ROUNDS, production_gensalt

MIN_PRODUCTION_ROUNDS = 12
"""Mặc định của thư viện ``bcrypt`` và là mức production đang chạy. Hạ số này xuống
là một **quyết định an toàn**, không phải chỉnh hằng số — nếu phải hạ thì ghi lý do
vào PROJECT_STATE như mọi quyết định tự chốt khác (full-auto #3)."""


def _cost_of(hashed: str) -> int:
    """Chi phí nằm ngay trong chuỗi hash: ``$2b$<cost>$<salt+digest>``."""
    return int(hashed.split("$")[2])


def test_production_password_hashing_keeps_the_library_default_cost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Với ``gensalt`` thật, ``hash_password`` phải cho ra chi phí ≥ 12.

    Trả lại đúng hàm thật rồi gọi **chính** hàm của mã sản phẩm — không đọc mã nguồn,
    không tin mô tả. Test này cố ý tốn ≈0,6 s (một lần băm + một lần kiểm ở chi phí
    12); đó là giá của việc kiểm chứng thay vì phỏng đoán.
    """
    monkeypatch.setattr(bcrypt, "gensalt", production_gensalt)

    hashed = hash_password("MatKhauThatCuaNguoiDung2026")

    assert _cost_of(hashed) >= MIN_PRODUCTION_ROUNDS, (
        f"hash_password sinh chi phí {_cost_of(hashed)}, dưới mức production "
        f"{MIN_PRODUCTION_ROUNDS} — mã sản phẩm đang ghim một mức rẻ, "
        f"và phần còn lại của bộ test không thể thấy điều đó."
    )
    assert verify_password("MatKhauThatCuaNguoiDung2026", hashed)
    assert not verify_password("MatKhauSai", hashed)


def test_the_suite_is_actually_running_on_the_cheap_cost() -> None:
    """Mặt kia của cùng một đánh đổi: xác nhận phần tăng tốc **đang** có hiệu lực.

    Nếu ai đó gỡ bản vá trong ``conftest.py`` mà quên file này, test trên vẫn xanh và
    bộ test lặng lẽ chậm lại 132 giây, không ai được báo. Ở đây thì đỏ ngay.
    """
    assert _cost_of(hash_password("bat-ky")) == TEST_BCRYPT_ROUNDS


def test_an_explicit_cost_is_still_honoured() -> None:
    """Bản vá chỉ đổi **mặc định** — ai truyền ``rounds`` tường minh vẫn được tôn trọng.

    Quan trọng vì nó chứng minh phần tăng tốc không chặn đường bất kỳ mã nào cần tự
    chọn chi phí; nó chỉ thay con số dùng khi không ai nói gì.
    """
    assert _cost_of(bcrypt.hashpw(b"x", bcrypt.gensalt(6)).decode("ascii")) == 6
