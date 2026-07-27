"""Nền test tự chứng minh nó có thật — 3 test này PHẢI XANH.

Không có 3 test này thì mọi ``xfail`` ở ``test_inventory_races.py`` là vô nghĩa:
một harness không thực sự mở hai kết nối sẽ làm test đua "đỏ đúng như dự đoán" vì
lý do hoàn toàn khác. Đây là chỗ đóng B-09 và A-01 của kiểm toán 2026-07-26.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pharmacy_os.core.outbox.record import OutboxRecord
from pharmacy_os.core.outbox.repository import SqlAlchemyOutboxRepository


async def test_two_sessions_are_two_real_connections(
    session_a: AsyncSession, session_b: AsyncSession
) -> None:
    """Đóng nguyên nhân gốc của B-09.

    ``tests/integration`` dùng ``StaticPool`` ⇒ mọi "phiên" chia nhau **một** kết
    nối ⇒ hai giao dịch đồng thời không tồn tại được. Ở đây hai phiên phải là hai
    **backend process** khác nhau của Postgres.
    """
    pid_a = (await session_a.execute(text("SELECT pg_backend_pid()"))).scalar_one()
    pid_b = (await session_b.execute(text("SELECT pg_backend_pid()"))).scalar_one()
    assert pid_a != pid_b, "hai phiên đang dùng chung một kết nối — harness vô giá trị"


async def test_second_session_sees_the_first_commit(
    session_a: AsyncSession, session_b: AsyncSession
) -> None:
    """Hai phiên phải nhìn thấy commit của nhau — điều kiện cần của mọi test đua.

    Cũng là lý do harness này **không dùng được** mẹo "mở giao dịch rồi ROLLBACK"
    (0,5 ms) mà phải commit thật rồi ``TRUNCATE`` (362 ms).
    """
    tenant_id, batch_id, drug_id, branch_id = uuid4(), uuid4(), uuid4(), uuid4()
    insert = text(
        "INSERT INTO stock_balances (id, tenant_id, branch_id, drug_id, batch_id, quantity)"
        " VALUES (:id, :tenant_id, :branch_id, :drug_id, :batch_id, 42)"
    )
    params = {
        "id": uuid4(),
        "tenant_id": tenant_id,
        "branch_id": branch_id,
        "drug_id": drug_id,
        "batch_id": batch_id,
    }

    await session_a.execute(insert, params)
    before = (
        await session_b.execute(
            text("SELECT count(*) FROM stock_balances WHERE batch_id = :b"), {"b": batch_id}
        )
    ).scalar_one()
    assert before == 0, "B thấy dữ liệu A chưa commit — cách ly giao dịch sai"

    await session_a.commit()
    await session_b.rollback()  # kết thúc snapshot cũ của B, mở snapshot mới
    after = (
        await session_b.execute(
            text("SELECT count(*) FROM stock_balances WHERE batch_id = :b"), {"b": batch_id}
        )
    ).scalar_one()
    assert after == 1, "B không thấy commit của A — hai phiên không độc lập thật"


async def test_for_update_skip_locked_is_actually_honoured(
    session_a: AsyncSession, session_b: AsyncSession
) -> None:
    """Đóng A-01: khoá hàng bị SQLite **nuốt im lặng**, ở đây phải có răng thật.

    ``SqlAlchemyOutboxRepository.claim_pending`` là 1 trong đúng 2 chỗ dùng
    ``FOR UPDATE SKIP LOCKED``. Trên SQLite, SQLAlchemy bỏ lặng mệnh đề đó nên hai
    relay chạy song song **cùng nhận một sự kiện** mà bộ test cũ không thể phát
    hiện. Trên nền này: A giữ hàng ⇒ B phải bỏ qua, không phải nhận trùng.
    """
    now = datetime.now(UTC)
    repo_a = SqlAlchemyOutboxRepository(session_a)
    await repo_a.add(
        OutboxRecord(
            event_id=uuid4(),
            event_type="test.event",
            tenant_id=uuid4(),
            payload={"k": "v"},
            occurred_at=now,
        )
    )
    await session_a.commit()

    claimed_a = await repo_a.claim_pending(now, limit=10)
    assert len(claimed_a) == 1, "A phải nhận được sự kiện PENDING duy nhất"

    # A vẫn giữ khoá (chưa commit). B phải thấy KHÔNG CÒN GÌ để nhận.
    repo_b = SqlAlchemyOutboxRepository(session_b)
    claimed_b = await repo_b.claim_pending(now, limit=10)
    assert claimed_b == [], (
        "B nhận lại đúng sự kiện A đang giữ — FOR UPDATE SKIP LOCKED không có hiệu "
        "lực trên nền này, tức A-01 vẫn mở"
    )
