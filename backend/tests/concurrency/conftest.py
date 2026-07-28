"""Nền test đồng thời: Postgres THẬT, hai kết nối ĐỘC LẬP thật.

**Vì sao thư mục này tồn tại** (F-4, sinh từ kiểm toán 2026-07-26 — B-09, A-01):
`tests/integration/conftest.py` dựng engine SQLite in-memory với ``StaticPool``,
nghĩa là **đúng một kết nối dùng chung cho cả bộ test**. Hai giao dịch đồng thời
vì thế **bất khả thi về mặt vật lý** — "0/1001 test đồng thời" không phải sơ suất
của người viết test mà là thứ nền test cũ **không biểu đạt được**. Thêm nữa,
SQLAlchemy **bỏ lặng** mệnh đề ``FOR UPDATE [SKIP LOCKED]`` trên SQLite, nên hai
chỗ khoá hàng duy nhất của hệ thống (``core/outbox/repository.py``,
``compliance/infrastructure/repository.py``) chưa từng được kiểm chứng.

Nền này KHÔNG thay thế ``tests/integration`` — nó là thư mục **mới**, không đụng
một dòng nào trong 1001 test hiện có (quyết định của Chain 2026-07-27, §7bh).

**Bốn ràng buộc thiết kế, đừng nới ra khi sửa file này:**

1. ``NullPool``, không ``StaticPool``. Mỗi session lấy một kết nối riêng — đó
   chính là điểm khác biệt làm test đồng thời trở nên khả thi.
2. **Guard tên CSDL.** Từ chối chạy nếu tên CSDL không kết thúc bằng ``_test``.
   Trỏ nhầm vào ``pharmacy_os`` dev là rủi ro DUY NHẤT của F-4 không hoàn tác
   được bằng ``git revert`` (harness ``TRUNCATE`` 9 bảng mỗi test).
3. **FAIL, KHÔNG SKIP** khi Postgres không chạy. Skip lặng rồi báo "xanh" đúng
   là bệnh "niềm tin giả" mà cả đợt kiểm toán chỉ ra.
4. **Interleaving tất định, CẤM ``sleep``.** Dùng :class:`StatementGate` — chặn
   đúng câu lệnh SQL cần chặn và mở bằng ``asyncio.Event``. Một test đỏ ngẫu
   nhiên 8% đã từng làm mất giá trị của chính cái cổng nó bảo vệ (§7ay).
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from sqlalchemy.util import await_only

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.inventory.application import InventoryService
from pharmacy_os.modules.inventory.domain.ports import BatchRepository
from pharmacy_os.modules.inventory.infrastructure import (
    SqlAlchemyBalanceRepository,
    SqlAlchemyBatchRepository,
    SqlAlchemyMovementRepository,
    SqlAlchemyStockReconciliationRepository,
)

DB_URL_ENV = "PHARMACY_CONCURRENCY_DB_URL"
"""Ghi đè URL CSDL test. Vẫn phải kết thúc ``_test`` — guard không có đường vòng."""

DEFAULT_DB_URL = "postgresql+asyncpg://pharma:pharma@localhost:5432/pharmacy_os_test"
"""Mặc định: Postgres của ``docker compose`` sẵn có, CSDL RIÊNG cạnh ``pharmacy_os``."""

REQUIRED_DB_SUFFIX = "_test"

TRUNCATED_TABLES = (
    "product_batches",
    "stock_movements",
    "stock_balances",
    "stock_reconciliation_needed",
    "sales_orders",
    "sale_lines",
    "sale_payments",
    "event_outbox",
    "audit_logs",
    "purchase_orders",
    "purchase_order_counters",
)
"""11 bảng trong phạm vi test đồng thời (9 từ F-4, +2 khi B3 thêm cấp phát mã PO).
``TRUNCATE`` cả 9 = 362 ms/test (đo 2026-07-27); ``TRUNCATE`` cả 48 bảng = 946 ms —
không cần, nên không làm.

Mẹo "mở giao dịch rồi ``ROLLBACK``" (0,5 ms) **không dùng được ở đây**: hai phiên
phải nhìn thấy commit của nhau, nên phải commit thật rồi dọn thật."""

HANG_GUARD_SECONDS = 30.0
"""Chặn treo, KHÔNG phải cơ chế đồng bộ. Đồng bộ là ``asyncio.Event`` trong
:class:`StatementGate`; timeout này chỉ để một bên chết giữa chừng không làm cả
bộ test treo vô hạn."""


# ---------------------------------------------------------------------------
# Guard + bootstrap CSDL
# ---------------------------------------------------------------------------
def _guarded_url() -> URL:
    """URL CSDL test, đã qua guard tên. Sai tên ⇒ nổ ngay, không cảnh báo rồi chạy tiếp."""
    url = make_url(os.environ.get(DB_URL_ENV, DEFAULT_DB_URL))
    if not (url.database or "").endswith(REQUIRED_DB_SUFFIX):
        raise RuntimeError(
            f"Từ chối chạy test đồng thời trên CSDL {url.database!r}: harness "
            f"TRUNCATE {len(TRUNCATED_TABLES)} bảng mỗi test, nên tên CSDL BẮT BUỘC "
            f"kết thúc bằng {REQUIRED_DB_SUFFIX!r}. Đặt {DB_URL_ENV} nếu cần URL khác."
        )
    return url


def _ensure_database(sync_url: URL) -> None:
    """Tạo CSDL test nếu chưa có. Postgres không chạy ⇒ FAIL kèm cách sửa, không SKIP."""
    admin = sync_url.set(database="postgres")
    engine = create_engine(admin, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": sync_url.database},
            ).scalar_one_or_none()
            if exists is None:
                conn.execute(text(f'CREATE DATABASE "{sync_url.database}"'))
    except OperationalError as exc:
        raise RuntimeError(
            f"Không kết nối được Postgres tại {admin.host}:{admin.port} — test đồng "
            f"thời KHÔNG được skip khi thiếu hạ tầng (skip lặng rồi báo xanh chính là "
            f"lỗi kiểm toán đang sửa). Chạy `make up` rồi thử lại.\nGốc: {exc}"
        ) from exc
    finally:
        engine.dispose()


BACKEND_ROOT = Path(__file__).resolve().parents[2]
"""Thư mục chứa ``alembic.ini`` — nơi ``alembic upgrade`` phải chạy từ đó."""


def _reset_legacy_schema(sync_url: URL) -> None:
    """Xoá sạch lược đồ nếu CSDL test được dựng bằng ``create_all`` (không có vết alembic).

    Không có ``alembic_version`` mà lại có bảng ⇒ đây là CSDL do bản conftest cũ
    dựng. Không thể "nâng cấp" nó: alembic sẽ chạy migration đầu tiên và đâm vào
    bảng đã tồn tại. Đường duy nhất đúng là làm lại từ số không.

    An toàn vì đây là hành động **duy nhất** đứng sau guard tên CSDL — tên không kết
    thúc ``_test`` thì :func:`_guarded_url` đã nổ từ trước, chưa câu lệnh nào chạm dữ liệu.
    """
    engine = create_engine(sync_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            tables = set(inspect(conn).get_table_names())
            if not tables or "alembic_version" in tables:
                return
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    finally:
        engine.dispose()


def _upgrade_to_head(sync_url: URL) -> None:
    """Chạy ``alembic upgrade head`` thật, trong **tiến trình con**.

    Tiến trình con chứ không phải gọi ``alembic.command`` tại chỗ: ``migrations/env.py``
    lấy URL từ ``get_settings()``, mà ``get_settings`` có ``@lru_cache``. Đổi biến môi
    trường rồi xoá cache ngay trong tiến trình test là để lại một quả mìn — mọi test
    chạy sau sẽ đọc phải cấu hình đã bị sửa. Tiến trình con thì không thể rò rỉ.
    """
    env = {**os.environ, "DB__URL": sync_url.render_as_string(hide_password=False)}
    done = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if done.returncode != 0:
        raise RuntimeError(
            "`alembic upgrade head` thất bại trên CSDL test — lược đồ KHÔNG dựng được, "
            "không có đường vòng nào (dựng bằng `create_all` chính là con bug vừa sửa).\n"
            f"Mã thoát: {done.returncode}\nstdout:\n{done.stdout}\nstderr:\n{done.stderr}"
        )


@pytest.fixture(scope="session")
def concurrency_db_url() -> str:
    """Bootstrap một lần cho cả phiên: guard tên → tạo CSDL nếu thiếu → **alembic upgrade head**.

    **Vì sao alembic chứ không phải ``create_all``** (nợ nền F-4, đóng 2026-07-27):
    ``create_all`` đọc model Python và **chỉ tạo bảng còn thiếu** — nó không thêm
    ràng buộc vào bảng đã tồn tại và không biết migration là gì. Hệ quả đã xảy ra
    thật ngay trong phiên F-5: máy đã có sẵn ``pharmacy_os_test`` từ trước thì
    **không nhận** ``uq_movement_ref_batch``, và 2 test B-02 đỏ vì **hạ tầng**, không
    vì mã sản phẩm — đúng cái bệnh "hạ tầng hỏng đội lốt bug thật" mà chính thư mục
    này được dựng lên để chống.

    Sâu hơn chuyện tiện lợi: bộ test đồng thời tồn tại để nói *"cái chạy trên
    production hành xử thế này"*. Lược đồ suy ra từ model Python **không phải** cái
    chạy trên production — cái đó là chuỗi migration. Suy từ model là kiểm chứng hệ
    thống bằng một bản sao của chính niềm tin đang cần kiểm chứng.

    Cố ý dùng driver **đồng bộ** (psycopg2): chạy ngoài mọi event loop nên không
    vướng loop-scope của ``pytest-asyncio`` khi fixture là session-scoped.
    """
    url = _guarded_url()
    sync_url = url.set(drivername="postgresql+psycopg2")
    _ensure_database(sync_url)
    _reset_legacy_schema(sync_url)
    _upgrade_to_head(sync_url)
    return url.render_as_string(hide_password=False)


# ---------------------------------------------------------------------------
# Engine / session — hai kết nối THẬT
# ---------------------------------------------------------------------------
def _make_engine(url: str) -> AsyncEngine:
    """``NullPool``: mỗi session lấy một kết nối riêng.

    Đây là toàn bộ lý do thư mục này tồn tại — ``StaticPool`` của
    ``tests/integration`` dùng chung 1 kết nối, hai phiên đồng thời không thể có.
    """
    return create_async_engine(url, poolclass=NullPool)


@pytest.fixture
async def engine_a(concurrency_db_url: str) -> AsyncIterator[AsyncEngine]:
    """Engine của quầy A. **Engine riêng, không dùng chung với B** — :class:`StatementGate`
    móc vào ``engine.sync_engine`` nên hai quầy phải có hai engine mới chặn riêng được."""
    engine = _make_engine(concurrency_db_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def engine_b(concurrency_db_url: str) -> AsyncIterator[AsyncEngine]:
    """Engine của quầy B."""
    engine = _make_engine(concurrency_db_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def pg_engine(concurrency_db_url: str) -> AsyncIterator[AsyncEngine]:
    """Engine trung lập: dọn bảng, dựng dữ liệu nền, đọc kết quả cuối. Không bị chặn."""
    engine = _make_engine(concurrency_db_url)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables(pg_engine: AsyncEngine) -> AsyncIterator[None]:
    """Dọn TRƯỚC mỗi test, không phải sau — test đỏ để lại dữ liệu để soi tận nơi."""
    async with pg_engine.begin() as conn:
        await conn.execute(
            text(f"TRUNCATE TABLE {', '.join(TRUNCATED_TABLES)} RESTART IDENTITY CASCADE")
        )
    yield


def _factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture
def factory_a(engine_a: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return _factory(engine_a)


@pytest.fixture
def factory_b(engine_b: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return _factory(engine_b)


@pytest.fixture
def session_factory(pg_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Factory trung lập (dựng nền / đọc kết quả). Quầy A và B dùng :func:`factory_a`/
    :func:`factory_b`."""
    return _factory(pg_engine)


@pytest.fixture
async def session_a(factory_a: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Quầy A."""
    async with factory_a() as session:
        yield session


@pytest.fixture
async def session_b(factory_b: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Quầy B — kết nối KHÁC hẳn quầy A, không phải cùng một kết nối đội hai tên."""
    async with factory_b() as session:
        yield session


@pytest.fixture
async def observer(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Kết nối thứ ba, chỉ để đọc kết quả cuối sau khi A và B đã commit."""
    async with session_factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Interleaving tất định
# ---------------------------------------------------------------------------
class StatementGate:
    """Chặn một phiên ngay TRƯỚC một câu lệnh SQL, mở ra khi được lệnh.

    Cho phép dựng đúng thứ tự "A đọc → B đọc → A ghi+commit → B ghi+commit" mà
    **không dùng ``sleep``**: :attr:`arrived` báo bên kia đã tới nơi, :attr:`release`
    là cái mở cửa. Cả hai là ``asyncio.Event`` — chờ sự kiện, không chờ đồng hồ.

    Móc vào ``before_cursor_execute`` (hook đồng bộ của SQLAlchemy) và ``await``
    trong đó bằng :func:`sqlalchemy.util.await_only`, hợp lệ vì hook chạy sẵn trong
    greenlet async của SQLAlchemy. Không đụng một dòng mã sản phẩm nào.
    """

    def __init__(self, engine: AsyncEngine, statement_prefix: str) -> None:
        self.arrived = asyncio.Event()
        self.release = asyncio.Event()
        self._prefix = statement_prefix
        self._armed = True

        @event.listens_for(engine.sync_engine, "before_cursor_execute")
        def _hold(  # type: ignore[no-untyped-def]
            conn, cursor, statement, parameters, context, executemany
        ) -> None:
            if self._armed and statement.lstrip().startswith(self._prefix):
                self._armed = False  # chỉ chặn lần đầu; các lệnh sau đi thẳng
                self.arrived.set()
                await_only(self.release.wait())

    def open(self) -> None:
        self.release.set()


async def both_arrived(*gates: StatementGate) -> None:
    """Chờ tới khi MỌI cổng đã có người đứng đợi — điểm "cả hai đã đọc xong"."""
    await asyncio.wait_for(
        asyncio.gather(*(g.arrived.wait() for g in gates)), timeout=HANG_GUARD_SECONDS
    )


async def finish(*tasks: asyncio.Task[None]) -> None:
    """Chờ các bên chạy nốt, có chặn treo."""
    await asyncio.wait_for(asyncio.gather(*tasks), timeout=HANG_GUARD_SECONDS)


# ---------------------------------------------------------------------------
# Ngữ cảnh + dịch vụ
# ---------------------------------------------------------------------------
@pytest.fixture
def ctx() -> RequestContext:
    """Một nhà thuốc, một chi nhánh — hai quầy bán cùng lúc dùng CHUNG ngữ cảnh này."""
    return RequestContext(
        tenant_id=uuid4(),
        branch_id=uuid4(),
        user_id=uuid4(),
        permissions=frozenset(
            {
                "inventory.read",
                "inventory.receive",
                "inventory.dispense",
                "inventory.reconcile",
            }
        ),
    )


class RecordingBus(InMemoryEventBus):
    """Ghi lại mọi sự kiện đã phát, để test khẳng định "sự kiện X ĐÃ/CHƯA được phát".

    Cần vì B-04 không chỉ là "số dư sai" — kiểm toán nêu rõ *"không phát
    ``StockShortfallDetected``, không dòng đối soát"*: hàng biến mất **và** không để
    lại vết nào cho người vận hành lần ra.
    """

    def __init__(self) -> None:
        super().__init__()
        self.published: list[object] = []

    async def publish(self, event: object) -> None:
        self.published.append(event)
        await super().publish(event)  # type: ignore[arg-type]

    def of_type(self, event_type: type) -> list[object]:
        return [e for e in self.published if isinstance(e, event_type)]


def build_inventory_service(
    session_factory: async_sessionmaker[AsyncSession],
    bus: InMemoryEventBus,
    *,
    batch_repo_factory: Callable[[UnitOfWork, RequestContext], BatchRepository] | None = None,
) -> InventoryService:
    """``InventoryService`` nối dây thật, mỗi UoW mở phiên riêng từ *session_factory*.

    Hai quầy = hai dịch vụ trên hai engine, đúng như hai tiến trình worker ngoài đời:
    dùng chung CSDL, không dùng chung kết nối, không dùng chung event bus.
    """

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, bus)

    return InventoryService(
        uow_factory,
        batch_repo_factory or (lambda uow, c: SqlAlchemyBatchRepository(uow.session, c)),
        lambda uow, c: SqlAlchemyMovementRepository(uow.session, c),
        lambda uow, c: SqlAlchemyBalanceRepository(uow.session, c),
        lambda uow, c: SqlAlchemyStockReconciliationRepository(uow.session, c),
        AuditLogger(session_factory),
    )


@pytest.fixture
def bus_a() -> RecordingBus:
    return RecordingBus()


@pytest.fixture
def bus_b() -> RecordingBus:
    return RecordingBus()


@pytest.fixture
def service_a(factory_a: async_sessionmaker[AsyncSession], bus_a: RecordingBus) -> InventoryService:
    """Kho hàng nhìn từ quầy A."""
    return build_inventory_service(factory_a, bus_a)


@pytest.fixture
def service_b(factory_b: async_sessionmaker[AsyncSession], bus_b: RecordingBus) -> InventoryService:
    """Kho hàng nhìn từ quầy B."""
    return build_inventory_service(factory_b, bus_b)


@pytest.fixture
def seeder(session_factory: async_sessionmaker[AsyncSession]) -> InventoryService:
    """Dịch vụ trên engine trung lập, chỉ dùng để **nhập kho dựng nền** trước khi đua.

    Cố ý tách khỏi ``service_a``: nếu dùng chính engine của quầy A để dựng nền thì
    :class:`StatementGate` sẽ chặn nhầm câu lệnh của bước dựng nền.
    """
    return build_inventory_service(session_factory, InMemoryEventBus())
