"""Mã sự cố truy được (F-18a) — `core/observability.py`.

Mệnh đề trung tâm: **cùng một mã** phải xuất hiện ở cả ba chỗ — header phản hồi, dòng log, và
thân `problem+json` người dùng đọc trên màn hình. Ba chỗ ấy nằm ở ba hệ thống khác nhau (HTTP,
structlog, JSON), và **không trình biên dịch nào nối được chúng** — đúng họ "chuỗi nối hai thế
giới" của kỷ luật #22, nên phải có cổng đọc thẳng cả ba.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine

from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.core.observability import REQUEST_ID_HEADER, _hop_le
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from tests.conftest import urls_csdl_thu


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "ma_su_co.db"
    _sync_url, _async_url = urls_csdl_thu(db_path)
    sync_engine = create_engine(_sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=_async_url),
        security=SecuritySettings(allow_dev_auth=True),
    )
    app = create_app(settings)

    # Một đường dẫn CỐ Ý NỔ, chỉ tồn tại trong test. Không thể dùng một endpoint thật để đo
    # nhánh 500: endpoint thật mà nổ được thì đó là một bug phải sửa, không phải một cố định
    # để test bám vào.
    no = APIRouter()

    @no.get("/no-tung-toe")
    async def _no() -> None:
        raise RuntimeError("nổ có chủ đích để đo nhánh 500")

    app.include_router(no)

    # `raise_server_exceptions=False` để TestClient trả phản hồi 500 THẬT thay vì ném lại
    # ngoại lệ vào test — nếu không, ta đo đường đi của pytest chứ không đo đường đi của
    # người dùng, và bộ xử lý 500 sẽ không bao giờ chạy.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_moi_phan_hoi_deu_mang_ma_su_co(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    ma = r.headers.get(REQUEST_ID_HEADER)
    assert ma and len(ma) == 12, f"mã phải đọc được qua điện thoại, nhận: {ma!r}"


def test_hai_request_hai_ma_khac_nhau(client: TestClient) -> None:
    """Mã dùng để phân biệt hai lần gọi — trùng nhau thì nó không phân biệt được gì."""
    a = client.get("/api/v1/health").headers[REQUEST_ID_HEADER]
    b = client.get("/api/v1/health").headers[REQUEST_ID_HEADER]
    assert a != b


def test_nhan_lai_ma_ben_goi_gui_de_ca_chuoi_dung_MOT_ma(client: TestClient) -> None:
    gui = "abcdef0123456789"
    r = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: gui})
    assert r.headers[REQUEST_ID_HEADER] == gui


@pytest.mark.parametrize(
    "xau",
    [
        "short",  # < 8 ký tự
        "x" * 65,  # > 64 ký tự
        "abcdef01; DROP TABLE",  # ký tự ngoài hex
        "abcdef01 khoang trang",
    ],
)
def test_tu_choi_ma_ben_goi_gui_khi_hinh_dang_SAI(client: TestClient, xau: str) -> None:
    """Header do máy khách gửi ⇒ dữ liệu không tin được. Cùng lý lẽ `client_ip_of` đã dùng
    khi từ chối tin `X-Forwarded-For`: chỗ nào ghi vào vết điều tra thì không được giả mạo."""
    r = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: xau})
    tra_ve = r.headers[REQUEST_ID_HEADER]
    assert tra_ve != xau, "mã sai hình dạng phải bị thay, không được dùng lại"
    assert len(tra_ve) == 12


@pytest.mark.parametrize(
    "xau",
    [
        "abcdef01\ndòng-log-giả",  # 🔴 xuống dòng — bẻ một dòng log thành nhiều dòng giả
        "abcdef01\r\nSet-Cookie: x",  # tách phản hồi HTTP
        "abcdef01\x00null",
        "ngắn",  # phi-ASCII
        "abcdef01" + "\t" * 3,
    ],
)
def test_hop_le_tu_choi_ky_tu_DIEU_KHIEN(xau: str) -> None:
    """🔴 Đo THẲNG `_hop_le`, không qua HTTP — và đó là điểm của test này.

    Bốn ca trên **không gửi qua `TestClient` được**: `httpx` từ chối mã hoá header phi-ASCII
    hoặc chứa ký tự xuống dòng, nên một test đi qua HTTP sẽ chết ở *máy khách* và **không bao
    giờ chạm tới** phép kiểm của máy chủ — nó xanh (hoặc đỏ) vì lý do hoàn toàn khác với mệnh
    đề nó tuyên bố. Đúng ca kỷ luật #14: *"một tín hiệu chứng minh mệnh đề KHÁC với mệnh đề
    người đọc tưởng nó chứng minh"*.

    Mà máy chủ **không được** dựa vào việc máy khách lịch sự: `curl --http1.0`, một proxy tự
    viết, hay một script Python gọi thẳng ASGI đều đưa được chuỗi này vào. Log của dự án là
    JSON một-dòng-một-bản-ghi ⇒ một mã chứa `\n` **chèn được dòng log giả** vào chính vết
    dùng để điều tra sự cố.
    """
    assert not _hop_le(xau)


def test_loi_khong_luong_truoc_tra_problem_json_MANG_MA(client: TestClient) -> None:
    """🔴 Mệnh đề đóng F-18a.

    Trước bản vá, ngoại lệ ngoài `AppError` trả `Internal Server Error` dạng **text/plain** —
    không phải problem+json như mọi lỗi khác — và dấu vết duy nhất là một traceback **không
    mang định danh nào**. Loại lỗi nghiêm trọng nhất lại là loại khó lần nhất.
    """
    r = client.get("/no-tung-toe")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/problem+json")

    body = r.json()
    ma_trong_than = body["ma_su_co"]
    ma_trong_header = r.headers[REQUEST_ID_HEADER]
    # Hai vế, hai nguồn độc lập (kỷ luật #23): một cái từ thân JSON, một cái từ header HTTP.
    assert ma_trong_than == ma_trong_header

    # Mã phải nằm trong câu người dùng ĐỌC ĐƯỢC, không chỉ trong một trường máy đọc — người
    # dược sĩ đọc câu tiếng Việt trên màn hình, không mở DevTools xem JSON.
    assert ma_trong_than in body["detail"]
    assert "báo mã sự cố" in body["detail"]


def test_loi_500_GIU_DUNG_ma_ben_goi_da_gui(client: TestClient) -> None:
    """🔴 Vế độc lập thật sự — và là mệnh đề DUY NHẤT bắt được lỗi mất `request.state`.

    Mệnh đề *"mã trong thân == mã trong header"* nghe như hai nguồn, nhưng ở đường đi lỗi cả
    hai đều do **cùng một dòng** trong bộ xử lý 500 sinh ra: mất `request.state` thì nó rơi về
    `ma_su_co_moi()` một lần rồi dùng cho cả hai chỗ — hai vế **luôn khớp**, và phép so là một
    phép gán đội lốt. Đo thật: đột biến bỏ `request.state.request_id = ma` trước `call_next`
    ⇒ `MUTANT2_EXIT=0`, cả 15 mệnh đề đều xanh. Đúng kỷ luật #23.

    Vế độc lập là **mã do máy khách tự chọn**: nó sinh ra bên ngoài tiến trình máy chủ, nên
    không dòng dự phòng nào bịa lại đúng nó được.
    """
    gui = "deadbeefcafe"
    r = client.get("/no-tung-toe", headers={REQUEST_ID_HEADER: gui})
    assert r.status_code == 500
    assert r.json()["ma_su_co"] == gui, "phản hồi lỗi phải giữ mã bên gọi đã gửi"
    assert r.headers[REQUEST_ID_HEADER] == gui


def test_than_loi_KHONG_ro_ri_noi_tang(client: TestClient) -> None:
    """Mã sự cố là **con trỏ tới log**, không phải bản sao của log."""
    body = client.get("/no-tung-toe").json()
    ca_than = json.dumps(body, ensure_ascii=False)
    for ro_ri in ("Traceback", "RuntimeError", "nổ có chủ đích", ".py", 'File "'):
        assert ro_ri not in ca_than, f"rò rỉ nội tạng: {ro_ri}"


def test_ma_CO_MAT_trong_dong_log(client: TestClient, capfd: pytest.CaptureFixture[str]) -> None:
    """🔴 Chỗ dễ hỏng lặng lẽ nhất của cả tính năng.

    Middleware có thể chạy đúng, header có thể trả đúng, thân JSON có thể mang mã đúng — mà
    log **vẫn không có mã nào**, nếu `structlog.contextvars.merge_contextvars` không nằm trong
    danh sách processor. Khi đó mọi mệnh đề khác vẫn xanh và tính năng vẫn chết: mã đọc qua
    điện thoại không `grep` ra dòng nào.

    Nên test này đọc **stdout thật**, không đọc lại biến trong tiến trình.
    """
    capfd.readouterr()  # bỏ phần trước đó
    ma = client.get("/api/v1/health").headers[REQUEST_ID_HEADER]
    ra = capfd.readouterr()
    dong_co_ma = [d for d in (ra.out + ra.err).splitlines() if ma in d]
    assert dong_co_ma, f"mã {ma} không xuất hiện trong bất kỳ dòng log nào"

    # Và nó phải nằm ở trường `request_id`, không phải tình cờ lọt vào một chuỗi khác.
    ban_ghi = [json.loads(d) for d in dong_co_ma if d.lstrip().startswith("{")]
    assert any(b.get("request_id") == ma for b in ban_ghi)


# ─────────────────────────────── /metrics (F-18b) ───────────────────────────────

_TOKEN = "token-thu-nghiem-chi-dung-trong-test"


@pytest.fixture
def client_co_metrics(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "metrics.db"
    _sync_url, _async_url = urls_csdl_thu(db_path)
    engine = create_engine(_sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    settings = Settings(
        app=AppSettings(env="dev", debug=True, metrics_token=SecretStr(_TOKEN)),
        db=DatabaseSettings(url=_async_url),
        security=SecuritySettings(allow_dev_auth=True),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def test_metrics_TAT_HAN_khi_khong_cau_hinh_token(client: TestClient) -> None:
    """Fail-closed: không khai token ⇒ endpoint **không được mount**, trả 404.

    404 chứ không 403 có chủ đích — một endpoint trả 403 là một endpoint **tự khai mình có
    tồn tại**. `/metrics` nói ra tổng lưu lượng và tỉ lệ lỗi của một cơ sở kinh doanh.
    """
    assert client.get("/metrics").status_code == 404


def test_metrics_doi_dung_token(client_co_metrics: TestClient) -> None:
    assert client_co_metrics.get("/metrics").status_code == 404
    assert (
        client_co_metrics.get("/metrics", headers={"Authorization": "Bearer sai"}).status_code
        == 404
    )
    r = client_co_metrics.get("/metrics", headers={"Authorization": f"Bearer {_TOKEN}"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/plain")


def test_metrics_dem_dung_so_request_va_so_loi(client_co_metrics: TestClient) -> None:
    """🔴 Hai vế, hai nguồn độc lập (kỷ luật #23).

    Vế `A` = số lần test **tự gọi** (đếm bằng vòng lặp trong test này). Vế `B` = con số máy
    chủ tự báo. Nếu lấy cả hai từ `/metrics` thì phép so là một phép gán đội lốt: nó xanh dù
    bộ đếm có cộng đúng hay không.
    """

    def doc(ten: str) -> float:
        body = client_co_metrics.get("/metrics", headers={"Authorization": f"Bearer {_TOKEN}"}).text
        for dong in body.splitlines():
            if dong.startswith(ten + " ") or dong.startswith(ten + "{"):
                return float(dong.rsplit(" ", 1)[1])
        raise AssertionError(f"không thấy {ten} trong:\n{body}")

    truoc = doc("pharmacy_requests_total")
    for _ in range(5):
        client_co_metrics.get("/api/v1/health")
    sau = doc("pharmacy_requests_total")
    # +5 lần gọi health, +1 lần gọi /metrics ở lượt `truoc` (chính nó cũng là một request).
    assert sau - truoc == 6, f"trước={truoc} sau={sau}"

    loi_truoc = doc('pharmacy_errors_total{lop="4xx"}')
    client_co_metrics.get("/api/v1/khong-ton-tai-dau")
    assert doc('pharmacy_errors_total{lop="4xx"}') > loi_truoc


def test_metrics_co_nguong_NFR_300ms_trong_bieu_do(client_co_metrics: TestClient) -> None:
    """Chỉ tiêu đã cam kết là **p95 < 300 ms @ 8 luồng** (§7br).

    Một biểu đồ tần suất không chứa đúng mốc mình cam kết thì không trả lời được câu *"có đạt
    không"* — nó chỉ trả lời được một câu gần giống, và người đọc sẽ tưởng là câu kia.
    """
    body = client_co_metrics.get("/metrics", headers={"Authorization": f"Bearer {_TOKEN}"}).text
    assert 'pharmacy_request_ms_bucket{le="300"}' in body
    assert 'pharmacy_request_ms_bucket{le="+Inf"}' in body
    assert "pharmacy_up 1" in body
    assert "pharmacy_uptime_seconds" in body
