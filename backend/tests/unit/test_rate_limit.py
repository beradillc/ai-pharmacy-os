"""Cửa sổ trượt của :mod:`core.security.rate_limit` — F-9.

Thời gian được **tiêm vào** qua tham số ``now``, không dùng ``sleep``: một test đo bằng
đồng hồ tường là một test đỏ ngẫu nhiên đang chờ ngày xảy ra (§7ay đã học một lần).
"""

from __future__ import annotations

import pytest

from pharmacy_os.core.security import RateLimiter, RateLimitRule

_RULE = RateLimitRule(max_events=3, window_seconds=60.0)


def test_allows_up_to_the_limit() -> None:
    limiter = RateLimiter()
    assert all(limiter.check("ip", _RULE, now=1.0).allowed for _ in range(3))


def test_blocks_the_one_past_the_limit() -> None:
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("ip", _RULE, now=1.0)
    verdict = limiter.check("ip", _RULE, now=1.0)
    assert not verdict.allowed
    assert verdict.retry_after_seconds > 0


def test_keys_are_independent() -> None:
    """Một IP bị chặn không được kéo theo IP khác — nếu không, chính cơ chế này thành DoS."""
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("ip-a", _RULE, now=1.0)
    assert not limiter.check("ip-a", _RULE, now=1.0).allowed
    assert limiter.check("ip-b", _RULE, now=1.0).allowed


def test_the_window_slides_instead_of_resetting() -> None:
    """Lượt cũ rời cửa sổ **từng cái một**, không xoá sạch theo mốc.

    Đây là điểm khác biệt thật giữa cửa sổ trượt và cửa sổ cố định: cửa sổ cố định cho
    bắn gấp đôi hạn mức quanh ranh giới.
    """
    limiter = RateLimiter()
    for t in (0.0, 10.0, 20.0):
        assert limiter.check("ip", _RULE, now=t).allowed
    assert not limiter.check("ip", _RULE, now=30.0).allowed
    # t=61: chỉ lượt ở t=0 hết hạn ⇒ đúng MỘT khe trống, không phải ba.
    assert limiter.check("ip", _RULE, now=61.0).allowed
    assert not limiter.check("ip", _RULE, now=61.0).allowed


def test_a_blocked_attempt_does_not_extend_the_block() -> None:
    """Lượt bị từ chối **không** được tính vào bộ đếm.

    Nếu tính, kẻ tấn công cứ bắn liên tục là tự giữ cửa sổ luôn đầy và người dùng thật
    không bao giờ vào lại được — hình phạt phải có điểm kết thúc.
    """
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("ip", _RULE, now=0.0)
    for t in (1.0, 2.0, 3.0, 59.0):  # bắn liên tục trong lúc đang bị chặn
        assert not limiter.check("ip", _RULE, now=t).allowed
    assert limiter.check("ip", _RULE, now=61.0).allowed


def test_retry_after_never_says_zero_seconds_while_blocked() -> None:
    """``Retry-After: 0`` là lời mời thử lại ngay — vô nghĩa với chính thứ vừa từ chối."""
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("ip", _RULE, now=0.0)
    assert limiter.check("ip", _RULE, now=59.99).retry_after_seconds >= 1


def test_reset_clears_one_key_only() -> None:
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("ip-a", _RULE, now=0.0)
        limiter.check("ip-b", _RULE, now=0.0)
    limiter.reset("ip-a")
    assert limiter.check("ip-a", _RULE, now=0.0).allowed
    assert not limiter.check("ip-b", _RULE, now=0.0).allowed


@pytest.mark.parametrize(
    ("max_events", "window"),
    [(0, 60.0), (-1, 60.0), (3, 0.0), (3, -1.0)],
)
def test_a_nonsensical_rule_is_refused_at_construction(max_events: int, window: float) -> None:
    """``max_events=0`` chặn tất cả mọi người — gần như chắc chắn là lỗi gõ, không phải ý đồ."""
    with pytest.raises(ValueError):
        RateLimitRule(max_events=max_events, window_seconds=window)
