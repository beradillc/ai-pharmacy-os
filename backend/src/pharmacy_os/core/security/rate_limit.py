"""Giới hạn tần suất theo IP cho các endpoint nhạy cảm — F-9 (kiểm toán B-10, C-11).

**Vì sao đây là mục chặn pilot, không phải "nên có".** Hệ thống đã có khoá tài khoản
sau N lần sai mật khẩu (``User.register_failed_attempt``). Khoá tài khoản **mà không**
giới hạn theo IP biến một cơ chế phòng thủ thành **vũ khí**: kẻ tấn công chỉ cần bắn
mật khẩu sai vào tài khoản của dược sĩ trưởng là khoá được người đó ra ngoài, lặp lại
cho từng tài khoản cho tới khi cả nhà thuốc không ai đăng nhập được. Không cần đoán
trúng mật khẩu nào cả. Đó là DoS bằng chính tính năng bảo mật.

Giới hạn theo IP đóng cửa đó: chi phí của kẻ tấn công chuyển từ *"một request mỗi tài
khoản"* sang *"một dải IP mỗi tài khoản"*.

**Cửa sổ trượt, không phải cửa sổ cố định.** Cửa sổ cố định cho phép bắn gấp đôi hạn
mức quanh ranh giới (cuối cửa sổ này + đầu cửa sổ sau). Với 5 lượt/phút thì đó là 10
lượt trong hai giây — đủ để hoàn tất một đợt dò mật khẩu ngắn.

**Trong tiến trình, không phải Redis — có chủ đích, và có hạn dùng.** Pilot là **một**
nhà thuốc trên **một** tiến trình ứng dụng; một bộ đếm trong RAM là đúng phạm vi và
không thêm một thành phần nữa có thể chết lúc 21 giờ. Khi chạy nhiều worker/nhiều máy,
bộ đếm này **đếm riêng từng tiến trình** và hạn mức thực tế nhân lên theo số worker —
xem :class:`RateLimiter` để biết chỗ cần đổi.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    """*max_events* lượt trong *window_seconds* giây."""

    max_events: int
    window_seconds: float

    def __post_init__(self) -> None:
        if self.max_events < 1:
            raise ValueError("max_events phải ≥ 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds phải > 0")


@dataclass(frozen=True, slots=True)
class RateLimitVerdict:
    allowed: bool
    retry_after_seconds: int
    """Số giây tới khi lượt cũ nhất rời cửa sổ. 0 khi được phép."""


class RateLimiter:
    """Cửa sổ trượt trong bộ nhớ, khoá theo chuỗi tuỳ ý (ở đây là IP + tên endpoint).

    **Đổi sang Redis ở đây và chỉ ở đây** khi triển khai nhiều worker: giữ nguyên
    :meth:`check`, thay phần lưu ``deque`` bằng một sorted set có TTL. Mọi nơi gọi
    đã đi qua đúng một cửa nên không chỗ nào khác phải sửa.

    Không tự dọn bằng nền chạy ngầm: mỗi lần :meth:`check` chạm một khoá thì khoá đó
    được cắt tỉa, và khoá không ai chạm nữa sẽ bị xoá khi rỗng. Một cái hẹn giờ nữa
    trong tiến trình là một thứ nữa có thể hỏng, đổi lấy chỗ nhớ không đáng kể.
    """

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, rule: RateLimitRule, *, now: float | None = None) -> RateLimitVerdict:
        """Ghi nhận một lượt và trả lời có cho qua không.

        Lượt **bị từ chối không được tính vào bộ đếm** — nếu tính, kẻ tấn công cứ bắn
        liên tục là tự giữ cho cửa sổ luôn đầy và người dùng thật không bao giờ vào lại
        được. Hình phạt phải có điểm kết thúc.
        """
        moment = time.monotonic() if now is None else now
        hits = self._hits[key]
        cutoff = moment - rule.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= rule.max_events:
            retry_after = max(1, int(hits[0] + rule.window_seconds - moment) + 1)
            return RateLimitVerdict(allowed=False, retry_after_seconds=retry_after)

        hits.append(moment)
        if not hits:  # pragma: no cover — chỉ để bất biến "khoá rỗng thì biến mất" rõ ràng
            del self._hits[key]
        return RateLimitVerdict(allowed=True, retry_after_seconds=0)

    def reset(self, key: str | None = None) -> None:
        """Xoá bộ đếm — dùng cho test và cho thao tác vận hành "mở khoá cho một IP"."""
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)
