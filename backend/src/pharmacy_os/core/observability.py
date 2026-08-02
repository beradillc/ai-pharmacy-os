"""Mã sự cố truy được — nối câu người dùng nói với dòng log của máy (F-18a).

🔴 **Vấn đề nó giải, nói bằng một cảnh có thật.** Dược sĩ gọi điện: *"sáng nay bấm Lưu nó báo
lỗi đỏ, giờ hết rồi"*. Trước tệp này, không có cách nào đi từ câu đó tới dòng log tương ứng:
màn hình hiện một câu tiếng Việt chung chung, log ghi một traceback không mang định danh nào,
và giữa hai thứ ấy **không có gì chung**. Người sửa phải đoán theo giờ, mà giờ thì cả trăm
request.

Nay mỗi request mang một **mã sự cố** ngắn. Nó xuất hiện ở đúng ba chỗ và chỉ ba chỗ đó:

    ① header `X-Request-Id` của mọi phản hồi
    ② mọi dòng log phát ra trong lúc xử lý request ấy (tự gắn, không phải nhớ truyền tay)
    ③ thân `problem+json` khi có lỗi — tức **thứ người dùng đọc được trên màn hình**

Dược sĩ đọc mã ấy qua điện thoại; người sửa `grep` một phát ra đúng request.

🔴 **Cố ý KHÔNG làm:** không trả traceback, không trả tên bảng/cột, không trả câu SQL cho máy
khách. Mã sự cố là **con trỏ tới log**, không phải bản sao của log. Một thông điệp lỗi kể chi
tiết nội tạng là thứ người dùng không sửa được gì với nó, còn kẻ tấn công thì có.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_log = structlog.get_logger("observability")

#: Tên header, dùng cho cả chiều nhận lẫn chiều trả. Chuẩn de-facto của hầu hết reverse proxy.
REQUEST_ID_HEADER = "X-Request-Id"

#: Độ dài mã đọc qua điện thoại. 12 ký tự hex = 48 bit ⇒ với vài chục nghìn request/ngày thì
#: xác suất trùng trong một ngày là không đáng kể, mà vẫn đọc được thành 3 cụm 4 ký tự.
#: UUID đầy đủ (36 ký tự) thì **không ai đọc qua điện thoại nổi** — và một mã người ta không
#: đọc nổi thì không bao giờ tới được người sửa, tức là bằng không.
_MA_DAI = 12


def ma_su_co_moi() -> str:
    return uuid.uuid4().hex[:_MA_DAI]


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Gắn mã sự cố vào **ngữ cảnh log** của toàn bộ request, rồi trả nó về trong header.

    Dùng ``structlog.contextvars`` chứ không truyền tay qua từng lớp: một mã chỉ hữu ích khi
    nó có mặt ở **mọi** dòng log của request đó, kể cả dòng do một service ở tầng sâu phát ra.
    Bắt mỗi lớp nhận thêm một tham số ``request_id`` là cách chắc chắn để vài chỗ quên.

    Nhận lại ``X-Request-Id`` do bên gọi gửi nếu có — để khi đặt sau một reverse proxy hoặc khi
    frontend tự sinh mã, cả chuỗi dùng **cùng một mã** thay vì mỗi tầng một mã khác nhau.

    🔴 **Chỉ nhận mã có hình dạng hợp lệ.** Header do máy khách gửi ⇒ nó là dữ liệu không tin
    được: một mã dài 4KB hay chứa ký tự xuống dòng sẽ đi thẳng vào log và **bẻ được từng dòng
    log thành nhiều dòng giả**. Đúng lý lẽ ``client_ip_of`` đã dùng khi từ chối tin
    ``X-Forwarded-For``: chỗ nào ghi vào vết kiểm toán thì chỗ đó không được giả mạo.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        gui_len = request.headers.get(REQUEST_ID_HEADER, "")
        ma = gui_len if _hop_le(gui_len) else ma_su_co_moi()

        # 🔴 Gán vào `request.state` **TRƯỚC** `call_next`, không phải sau. Khi handler ném
        # ngoại lệ, `call_next` ném theo và **mọi dòng phía sau nó không bao giờ chạy** — nên
        # đặt sau thì đúng ở đường đi bình thường và **hỏng đúng ở đường đi lỗi**, tức hỏng ở
        # chính ca mà cả tính năng này sinh ra để phục vụ. Bộ xử lý 500 đọc `request.state`.
        request.state.request_id = ma

        structlog.contextvars.bind_contextvars(request_id=ma)
        bat_dau = time.perf_counter()
        try:
            response = await call_next(request)
            # 🔴 Ghi log **TRƯỚC** khi gỡ ngữ cảnh. Bản đầu đặt `unbind` trong `finally` và
            # dòng `_log.info` ở sau khối `try` — mà `finally` chạy TRƯỚC, nên mã đã bị gỡ
            # đúng lúc dòng log được phát ra: header trả về đúng, thân JSON đúng, và log
            # **không có mã nào**. Cổng xanh, tính năng chết. Test `test_ma_CO_MAT_trong_dong_log`
            # bắt được ngay lượt chạy đầu.
            _log.info(
                "http_request",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=round((time.perf_counter() - bat_dau) * 1000, 1),
            )
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers[REQUEST_ID_HEADER] = ma
        return response


def _hop_le(ma: str) -> bool:
    """Hex, 8–64 ký tự. Hẹp có chủ đích — xem docstring middleware."""
    return 8 <= len(ma) <= 64 and all(c in "0123456789abcdefABCDEF-" for c in ma)


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    """Lỗi KHÔNG lường trước → 500 mang mã sự cố, và một dòng log mang đúng mã ấy.

    🔴 Trước bộ xử lý này, một ngoại lệ ngoài ``AppError`` đi thẳng ra ``ServerErrorMiddleware``
    của Starlette: máy khách nhận ``Internal Server Error`` dạng text/plain — **không phải
    problem+json** như mọi lỗi khác của API này — và dấu vết duy nhất là một traceback trên
    stdout **không mang định danh nào**. Nghĩa là đúng loại lỗi nghiêm trọng nhất lại là loại
    khó lần nhất.

    ``exc_info=True`` để traceback vào **log**, còn thân phản hồi **không mang traceback** —
    xem ghi chú đầu tệp.
    """
    ma = getattr(request.state, "request_id", None) or ma_su_co_moi()
    _log.error(
        "loi_khong_luong_truoc",
        request_id=ma,
        method=request.method,
        path=request.url.path,
        exc_info=exc,
    )
    # 🔴 Phải tự gắn header ở ĐÂY. Khi handler ném, phản hồi 500 do Starlette dựng **không đi
    # ngược qua middleware** nữa, nên dòng gán header trong `RequestIdMiddleware` không chạy.
    # Thiếu chỗ này thì đúng phản hồi lỗi — thứ duy nhất người dùng cần mã để báo — lại là
    # phản hồi **không mang mã trong header**.
    return JSONResponse(
        status_code=500,
        media_type="application/problem+json",
        headers={REQUEST_ID_HEADER: ma},
        content={
            "type": "https://errors.pharmacy-os/internal",
            "title": "Lỗi hệ thống",
            "status": 500,
            # Câu này hiện thẳng trên màn hình người dùng. Nó phải nói được ĐÚNG MỘT việc mà
            # người dùng làm được: đọc mã này cho người sửa.
            "detail": (
                f"Có lỗi ngoài dự kiến. Vui lòng báo mã sự cố {ma} cho người phụ trách "
                "kỹ thuật — mã này tra được đúng dòng nhật ký của lần lỗi vừa rồi."
            ),
            "instance": str(request.url.path),
            "ma_su_co": ma,
        },
    )


def register_observability(app: FastAPI) -> None:
    """Nối middleware mã sự cố + bộ xử lý 500.

    Gọi **sau** ``register_error_handlers``: ``AppError`` (400/401/403/404/409/422) đã có bộ xử
    lý riêng trả problem+json đúng nghiệp vụ, và những lỗi đó **không phải sự cố** — chúng là
    câu trả lời hợp lệ cho một yêu cầu sai. Chỉ thứ lọt qua hết mới là sự cố.
    """
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(Exception, _handle_unexpected)
