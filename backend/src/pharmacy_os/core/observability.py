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

import secrets
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
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
            _do = getattr(request.app.state, "so_do", None)
            if _do is not None:
                _do.ghi(response.status_code, (time.perf_counter() - bat_dau) * 1000)
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
    # Đặt trên `app.state` chứ không trong container, cùng lý lẽ `rate_limiter` (F-9): đây là
    # trạng thái của **tiến trình phục vụ HTTP**, không phải một dịch vụ nghiệp vụ — và mỗi
    # TestClient dựng app riêng nên bộ test không rò số đo từ test này sang test khác.
    app.state.so_do = SoDo()
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(Exception, _handle_unexpected)


# ─────────────────────────────── Số đo (F-18b) ───────────────────────────────
#
# 🔴 **Vì sao TỰ VIẾT, không thêm `prometheus-client`.** Không phải vì ngại phụ thuộc — dự án
# này thêm `cryptography` và `pyotp` không do dự, đúng chỗ không được tự viết. Lý do là **quy
# mô câu hỏi**: một nhà thuốc 2–3 quầy cần trả lời đúng bốn câu — *máy còn sống không · có
# đang lỗi không · lỗi bao nhiêu · chậm cỡ nào*. Bốn bộ đếm nguyên và một biểu đồ tần suất
# thô trả lời hết. `prometheus-client` là thư viện cho hệ nhiều tiến trình, nhiều nhãn, có
# máy chủ scrape — dự án này **chưa có máy chủ scrape nào**, và một tệp `/metrics` không ai
# đọc là đúng hình dạng `ci.yml`: hạ tầng viết sẵn, không nối dây, bằng không (kiểm toán C-03).
#
# Nên: định dạng văn bản Prometheus (để ngày mai cắm scraper vào là chạy) **cộng với**
# `scripts/health_deadman.sh` đọc nó ngay hôm nay — cùng khuôn `backup_deadman.sh` đã có và
# đã chứng minh được trong repo này.
#
# Giới hạn khai rõ, không giấu: bộ đếm sống **trong tiến trình**, mất khi khởi động lại, và
# **không cộng được qua nhiều worker uvicorn**. Chạy `--workers > 1` thì mỗi worker báo phần
# của nó. Với một quầy thuốc chạy một tiến trình thì đúng; vượt quy mô đó thì đây là lúc
# thay bằng `prometheus-client` + multiprocess mode, không phải vá tệp này.

_BUCKET_MS: tuple[float, ...] = (50.0, 100.0, 300.0, 1000.0, 3000.0)
"""Mốc tần suất, tính bằng mili giây. `300` có mặt vì đó là **chỉ tiêu NFR đã chốt**
(p95 < 300 ms @ 8 luồng, §7br) — một biểu đồ tần suất không chứa đúng ngưỡng mình cam kết
thì không trả lời được câu *"có đạt không"*."""


class SoDo:
    """Bộ đếm tiến trình: tổng request, tổng lỗi, và phân bố độ trễ.

    Cố ý **không có nhãn theo đường dẫn**. Một quầy thuốc có ~40 endpoint; gắn nhãn đường dẫn
    là nhân số dòng lên 40 lần để đổi lấy thứ mà log ``http_request`` (đã có ``path``,
    ``status``, ``ms`` từ B1a) trả lời tốt hơn. Số đo ở đây để **cảnh báo**, log để **điều
    tra** — trộn hai việc thì được một thứ làm cả hai đều tệ.
    """

    def __init__(self) -> None:
        self.tong = 0
        self.loi_5xx = 0
        self.loi_4xx = 0
        self.tong_ms = 0.0
        self.buckets: dict[float, int] = dict.fromkeys(_BUCKET_MS, 0)
        self.khoi_dong = time.time()

    def ghi(self, status: int, ms: float) -> None:
        self.tong += 1
        self.tong_ms += ms
        if status >= 500:
            self.loi_5xx += 1
        elif status >= 400:
            self.loi_4xx += 1
        for moc in _BUCKET_MS:
            if ms <= moc:
                self.buckets[moc] += 1

    def phoi_bay(self) -> str:
        """Định dạng văn bản Prometheus 0.0.4 — ``# HELP``/``# TYPE`` rồi mẫu, mỗi thứ một dòng."""
        d: list[str] = [
            "# HELP pharmacy_up Tiến trình còn phục vụ (bằng 1 nếu đọc được dòng này).",
            "# TYPE pharmacy_up gauge",
            "pharmacy_up 1",
            "# HELP pharmacy_uptime_seconds Số giây kể từ lần khởi động gần nhất.",
            "# TYPE pharmacy_uptime_seconds gauge",
            f"pharmacy_uptime_seconds {time.time() - self.khoi_dong:.0f}",
            "# HELP pharmacy_requests_total Tổng số request đã phục vụ.",
            "# TYPE pharmacy_requests_total counter",
            f"pharmacy_requests_total {self.tong}",
            "# HELP pharmacy_errors_total Số phản hồi lỗi, tách theo lớp mã trạng thái.",
            "# TYPE pharmacy_errors_total counter",
            f'pharmacy_errors_total{{lop="4xx"}} {self.loi_4xx}',
            f'pharmacy_errors_total{{lop="5xx"}} {self.loi_5xx}',
            "# HELP pharmacy_request_ms Phân bố độ trễ (mili giây).",
            "# TYPE pharmacy_request_ms histogram",
        ]
        d.extend(
            f'pharmacy_request_ms_bucket{{le="{moc:.0f}"}} {self.buckets[moc]}'
            for moc in _BUCKET_MS
        )
        d.append(f'pharmacy_request_ms_bucket{{le="+Inf"}} {self.tong}')
        d.append(f"pharmacy_request_ms_sum {self.tong_ms:.1f}")
        d.append(f"pharmacy_request_ms_count {self.tong}")
        return "\n".join(d) + "\n"


def register_metrics_endpoint(app: FastAPI, token: str) -> None:
    """Mount ``GET /metrics`` — **chỉ khi** có token cấu hình.

    Đặt ngoài ``/api/v1`` có chủ đích: nó không phải API nghiệp vụ, không có phiên bản, và
    không nên xuất hiện trong OpenAPI của khách hàng (``include_in_schema=False``).

    So token bằng :func:`secrets.compare_digest` chứ không bằng ``==``: phép so chuỗi thường
    thoát sớm ở ký tự đầu khác nhau, nên thời gian trả lời rò rỉ **độ dài tiền tố đúng** và
    đoán được từng ký tự. Cùng nguyên tắc đã áp cho chữ ký VNPAY.
    """
    if not token:
        _log.info("metrics_tat", ly_do="APP__METRICS_TOKEN rỗng — endpoint không được mount")
        return

    @app.get("/metrics", include_in_schema=False)
    async def _metrics(request: Request) -> Response:
        gui = request.headers.get("Authorization", "")
        gui = gui[7:] if gui.startswith("Bearer ") else gui
        if not secrets.compare_digest(gui, token):
            # 404 chứ không 403 — xem `AppSettings.metrics_token`.
            raise HTTPException(status_code=404)
        do: SoDo = request.app.state.so_do
        return PlainTextResponse(
            do.phoi_bay(), media_type="text/plain; version=0.0.4; charset=utf-8"
        )
