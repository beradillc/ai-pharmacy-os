"""Shared test fixtures — plus the one setting that decides how long the suite takes.

Nothing here changes what the code under test does; see :func:`_sqlite_test_pragmas`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import bcrypt
import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine

from pharmacy_os.core.config import (
    AISettings,
    AppSettings,
    DatabaseSettings,
    SecuritySettings,
    Settings,
)

_SQLITE_TEST_PRAGMAS = ("PRAGMA synchronous=OFF", "PRAGMA journal_mode=MEMORY")
"""Durability settings for **throwaway** SQLite databases. Measured, not guessed.

The e2e fixtures each build a fresh file-backed SQLite database and run
``create_all`` over **48 tables**. With SQLite's default ``synchronous=FULL`` that
is an ``fsync`` per DDL statement, and it costs **≈2.0 s per test** — on a suite
where the whole of ``tests/unit`` (453 tests) runs in 4,6 s.

Measured on this machine 2026-07-27, ``create_all`` of the full metadata:

===================================================  ==========
file-backed SQLite, defaults (what the suite did)     2004,1 ms
same file, these two pragmas                            47,5 ms
in-memory SQLite (for comparison)                       36,4 ms
===================================================  ==========

So **≈98 % of that 2 s was waiting on the disk**, not building the schema. Turning
durability off is free here in the only sense that matters: these databases live in
``tmp_path`` and are deleted at the end of the test. A crash mid-test loses a
database we were going to throw away anyway.

**Deliberately scoped to SQLite.** ``tests/concurrency`` runs on real Postgres and
must keep real durability — that suite exists to prove locking behaviour, and a
weakened storage engine underneath it would quietly hollow out the very thing it
checks. The guard below keys off the driver, not off which fixture is asking.
"""


production_gensalt = bcrypt.gensalt
"""``bcrypt.gensalt`` thật, giữ lại **trước** khi thay — production dùng đúng cái này.

Không phải để dùng trong test thường. Nó tồn tại để
``test_password_hashing_cost.py`` khôi phục lại đúng hàm thật và chứng minh
production **không** bị kéo theo mức rẻ bên dưới. Bỏ tham chiếu này đi là bỏ luôn
khả năng chứng minh đó.
"""

TEST_BCRYPT_ROUNDS = 4
"""Chi phí bcrypt **chỉ trong bộ test**. Đo trên máy này 2026-07-27:

======  =========  ===========
rounds  băm        kiểm
======  =========  ===========
12       290,6 ms   291,6 ms
10        73,0 ms    72,2 ms
 8        18,5 ms    18,1 ms
 4         1,2 ms     1,2 ms
======  =========  ===========

Sau khi vá `fsync`, bcrypt là khoản lớn nhất còn lại: ``hashpw`` 225 lần (65,2 s)
+ ``checkpw`` 232 lần (67,3 s) = **132,5 s, tức 46,6 %** của ``tests/integration``.

**Đây là đánh đổi có thật, không phải bữa trưa miễn phí.** Bộ test không còn chạy
đúng chi phí băm của production, nên nếu ai đó ghim một mức rẻ vào chính mã sản
phẩm, những test này sẽ không thấy. Đổi lại, khoảng mù đó **được canh bằng một test
riêng** (``tests/unit/test_password_hashing_cost.py``) chứ không bỏ ngỏ — điều kiện
GĐ đặt ra khi duyệt, vì "khoảng mù không ai canh" đúng là hình dạng chung của 16 sự
cố *niềm tin giả* trong kiểm toán 2026-07-26.

Cái **không** đổi: vẫn là bcrypt thật, vẫn băm rồi kiểm lại thật, ``checkpw`` vẫn
đọc chi phí từ chính chuỗi hash. Chỉ có số vòng lặp là rẻ đi.
"""


def _fast_gensalt(rounds: int = TEST_BCRYPT_ROUNDS, prefix: bytes = b"2b") -> bytes:
    """``bcrypt.gensalt`` với mặc định rẻ. Ai truyền ``rounds`` tường minh vẫn được tôn trọng."""
    return production_gensalt(rounds, prefix)


bcrypt.gensalt = _fast_gensalt  # type: ignore[assignment]


@event.listens_for(Engine, "connect")
def _sqlite_test_pragmas(dbapi_connection: Any, connection_record: Any) -> None:
    """Apply :data:`_SQLITE_TEST_PRAGMAS` to every SQLite connection in the suite.

    Registered once, on the ``Engine`` class, so it reaches engines the test never
    sees — including the ones ``create_app`` builds inside the e2e fixtures. Doing
    it per-fixture instead would mean editing 21 files and getting it wrong in the
    22nd.
    """
    if "sqlite" not in type(dbapi_connection).__module__.lower():
        return  # Postgres (tests/concurrency) — leave durability alone
    cursor = dbapi_connection.cursor()
    try:
        for pragma in _SQLITE_TEST_PRAGMAS:
            cursor.execute(pragma)
    finally:
        cursor.close()


#: URL Postgres dùng-một-lần cho bộ test, đặt qua biến môi trường.
#:
#: 🔴 **Nợ F-4** (kiểm toán 2026-07-26 quy tắc R-7): bộ test chạy trên SQLite, và chênh lệch
#: dialect đã cho lọt **bốn lỗi thật** tới deployment —
#:   · `audit_logs.action` varchar(32) — 734 test vẫn xanh
#:   · tràn cột varchar hàng loạt — 6/7 endpoint thử trả 500
#:   · migration 0045 thiếu `server_default=now()` — **1439 test SQLite xanh hết**
#:   · nặng nhất: `FOR UPDATE SKIP LOCKED` bị SQLite **nuốt im lặng** ở đúng hai chỗ cần khoá
#:     hàng (audit A-01) ⇒ 1001 test **về cấu trúc không thể chứng minh** bản vá tồn kho đúng
#:
#: Cách dùng: `make test-pg`, hoặc `TEST_DB_URL=postgresql://… pytest`.
#:
#: Vì sao là **biến môi trường** chứ không đổi hẳn sang Postgres: SQLite trong bộ nhớ chạy
#: bộ test trong ~5 phút, Postgres thì chậm hơn nhiều và đòi một container đang chạy. Bắt mọi
#: lượt chạy tay phải có Postgres là cách người ta thôi chạy test. Hai nền, một bộ test —
#: SQLite cho vòng lặp nhanh, Postgres cho lượt trước khi đóng mục.
TEST_DB_URL = os.environ.get("TEST_DB_URL")

#: CSDL đã tạo cho mỗi `db_path` — xem chú thích trong `urls_csdl_thu`.
_CSDL_DA_TAO: dict[str, tuple[str, str]] = {}


def urls_csdl_thu(db_path: Path) -> tuple[str, str]:
    # ⚠️ KHÔNG đặt tên bắt đầu bằng `test_`: pytest thu mọi hàm `test_*` ở module cấp cao
    # thành một test, và nó sẽ đỏ với lỗi "fixture 'db_path' not found" ở 30 tệp cùng lúc —
    # một thông báo không chỉ được về nguyên nhân thật.
    """``(url đồng bộ, url bất đồng bộ)`` cho một bộ test — Postgres nếu có, không thì SQLite.

    Mọi tệp e2e gọi hàm này thay vì tự ghép chuỗi `sqlite:///…`. Tự ghép ở 35 chỗ nghĩa là
    35 chỗ phải sửa khi đổi nền, và cái thứ 36 sẽ bị quên.
    """
    if not TEST_DB_URL:
        return f"sqlite:///{db_path}", f"sqlite+aiosqlite:///{db_path}"

    # 🔴 NHỚ THEO `db_path`. Hàm này có **tác dụng phụ** — nó TẠO một CSDL, không chỉ ghép
    # một chuỗi. Ba tệp gọi nó hai lần (một lần trong fixture, một lần trong thân test để mở
    # engine đọc lại dữ liệu), và không có bộ nhớ này thì lượt hai tạo một CSDL **rỗng khác**
    # ⇒ 9 test đỏ với "không thấy dòng nào" trong lúc dòng đó nằm ở CSDL kia.
    #
    # Đo thật: 199 hỏng (chưa cách ly) → 9 hỏng (cách ly, chưa nhớ) → 0 (nhớ theo db_path).
    #
    # Bài học đáng giữ: một hàm tên như *tính toán* mà thực ra *tạo tài nguyên* thì gọi hai
    # lần là hai thứ khác nhau — và chỗ gọi không có cách nào biết điều đó.
    if str(db_path) in _CSDL_DA_TAO:
        return _CSDL_DA_TAO[str(db_path)]

    # 🔴 MỘT CSDL RIÊNG cho mỗi lượt gọi, không dùng chung.
    #
    # SQLite cho mỗi tệp test một *tệp* riêng dưới `tmp_path` ⇒ cách ly là miễn phí và
    # không ai phải nghĩ tới. Postgres thì không: lượt chạy đầu trên nền Postgres cho
    # **63 `UniqueViolation` + 42 "already exists"** — không phải lỗi sản phẩm, mà là mọi
    # tệp cùng ghi vào một CSDL và thấy dữ liệu của tệp chạy trước.
    #
    # Tạo CSDL rẻ (~100ms) và cách ly TUYỆT ĐỐI. Đắt hơn `TRUNCATE` nhưng `TRUNCATE` đòi
    # biết danh sách bảng — và danh sách đó sẽ lệch đúng vào lần thêm bảng tiếp theo.
    ten = f"beras_t_{abs(hash(str(db_path))) % 10**12:012d}"
    goc = TEST_DB_URL.rsplit("/", 1)[0]
    admin = create_engine(f"{goc}/postgres", isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as c:
            c.execute(text(f'DROP DATABASE IF EXISTS "{ten}"'))
            c.execute(text(f'CREATE DATABASE "{ten}"'))
    finally:
        admin.dispose()
    dong_bo = f"{goc}/{ten}"
    cap = (dong_bo, dong_bo.replace("postgresql://", "postgresql+asyncpg://", 1))
    _CSDL_DA_TAO[str(db_path)] = cap
    return cap


@pytest.fixture
def settings() -> Settings:
    """Deterministic settings using an in-memory SQLite DB for tests."""
    return Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=TEST_DB_URL or "sqlite+aiosqlite:///:memory:"),
        ai=AISettings(api_key="test-key"),  # type: ignore[arg-type]
        security=SecuritySettings(jwt_secret="test-secret-key-0123456789abcdef"),  # type: ignore[arg-type]
    )
