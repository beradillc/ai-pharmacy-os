"""``UyQuyenGuard`` — quyền mượn đọc lại mỗi request, trên CSDL thật.

🔴 **Mệnh đề đắt nhất: quyền mượn BIẾN MẤT đúng hạn mà KHÔNG cần cấp lại token.**

Đó chính là lý do cơ chế này không nằm trong JWT. Nếu quyền uỷ quyền đi vào token đã ký thì
một uỷ quyền 24 giờ **sống dai hơn cửa sổ của chính nó**: token cấp lúc 23:59 vẫn mang quyền
ấy cho tới khi token hết hạn. Test dưới đây đo đúng chỗ đó — cùng một "phiên", hai mốc thời
gian, hai câu trả lời khác nhau.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.db.base import Base
from pharmacy_os.core.security.uy_quyen_scope import UyQuyenGuard

pytestmark = pytest.mark.anyio

_QUYEN = frozenset({"crm.sensitive.read", "crm.read"})


async def _dung_tenant_va_nguoi(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[UUID, UUID, UUID]:
    """Một tenant + một người **có thật** trong bảng.

    🔴 Không dùng ``uuid4()`` rời: khoá ngoại ``nguoi_nhan_id -> users.id`` được cưỡng chế
    thật trong bộ test (``PRAGMA foreign_keys=ON``), và bản đầu của tệp này đỏ 3/4 vì thế.
    Ràng buộc bắt đúng thứ nó sinh ra để bắt — **không ghi được một uỷ quyền cho một người
    không tồn tại** — nên giữ nguyên nó và dựng dữ liệu cho đúng, thay vì tắt đi cho tiện.
    """
    tenants = Base.metadata.tables["tenants"]
    users = Base.metadata.tables["users"]
    tenant_id, user_id, nguoi_cap_id = uuid4(), uuid4(), uuid4()
    now = datetime(2026, 8, 1, tzinfo=UTC)
    async with session_factory() as session:
        await session.execute(
            tenants.insert().values(
                id=tenant_id, name="Nhà thuốc Bera", status="ACTIVE", created_at=now, updated_at=now
            )
        )
        await session.execute(
            users.insert().values(
                id=user_id,
                tenant_id=tenant_id,
                email="kythuat@bera.vn",
                password_hash="x",
                full_name="Trần Bảo Trì",
                status="ACTIVE",
                must_change_password=False,
                failed_login_count=0,
                created_at=now,
                updated_at=now,
            )
        )
        # Người CẤP là một tài khoản thứ hai, không phải chính người nhận: luật domain cấm
        # tự uỷ quyền cho chính mình, và một hàng mẫu vi phạm luật ấy sẽ được đọc như thể
        # nó hợp lệ bởi người sửa tệp này về sau.
        await session.execute(
            users.insert().values(
                id=nguoi_cap_id,
                tenant_id=tenant_id,
                email="chuchuoi@bera.vn",
                password_hash="x",
                full_name="Lê Chủ Chuỗi",
                status="ACTIVE",
                must_change_password=False,
                failed_login_count=0,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()
    return tenant_id, user_id, nguoi_cap_id


async def _ghi_uy_quyen(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    tenant_id: UUID,
    nguoi_nhan_id: UUID,
    nguoi_cap_id: UUID,
    cap_luc: datetime,
    thu_hoi_luc: datetime | None = None,
) -> None:
    """Ghi thẳng bằng SQL, **không** qua repository của ``iam``.

    Cố ý: guard này sống ở ``core`` và phải đúng với **cái bảng**, không phải với một lớp
    ánh xạ. Nếu test đi qua chính repository mà guard không dùng, hai vế của phép so lại về
    cùng một nguồn (kỷ luật #23) và test sẽ xanh cả khi câu SQL trong guard sai cột.
    """
    uy_quyen = Base.metadata.tables["uy_quyen_quan_tri"]
    quyen = Base.metadata.tables["uy_quyen_quan_tri_quyen"]
    uq_id = uuid4()
    async with session_factory() as session:
        await session.execute(
            uy_quyen.insert().values(
                id=uq_id,
                tenant_id=tenant_id,
                nguoi_nhan_id=nguoi_nhan_id,
                nguoi_cap_id=nguoi_cap_id,
                ly_do="Sửa lỗi hoá đơn tính sai tiền thối",
                cap_luc=cap_luc,
                het_han_luc=cap_luc + timedelta(hours=24),
                thu_hoi_luc=thu_hoi_luc,
            )
        )
        await session.execute(
            quyen.insert(), [{"uy_quyen_id": uq_id, "permission": p} for p in sorted(_QUYEN)]
        )
        await session.commit()


async def test_quyen_muon_HET_dung_han_ma_khong_can_cap_lai_token(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """🔴 Mệnh đề trung tâm — xem docstring đầu tệp."""
    guard = UyQuyenGuard(session_factory)
    tenant_id, user_id, nguoi_cap_id = await _dung_tenant_va_nguoi(session_factory)
    cap_luc = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    await _ghi_uy_quyen(
        session_factory,
        tenant_id=tenant_id,
        nguoi_nhan_id=user_id,
        nguoi_cap_id=nguoi_cap_id,
        cap_luc=cap_luc,
    )

    trong_han = await guard.quyen_duoc_uy_quyen(
        tenant_id, user_id, cap_luc + timedelta(hours=23, minutes=59)
    )
    qua_han = await guard.quyen_duoc_uy_quyen(
        tenant_id, user_id, cap_luc + timedelta(hours=24, minutes=1)
    )

    assert trong_han == _QUYEN
    assert qua_han == frozenset(), (
        "Quyền mượn phải tự hết đúng hạn. Còn sót nghĩa là cơ chế 24 giờ chỉ là hình thức."
    )


async def test_thu_hoi_som_co_hieu_luc_ngay(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    guard = UyQuyenGuard(session_factory)
    tenant_id, user_id, nguoi_cap_id = await _dung_tenant_va_nguoi(session_factory)
    cap_luc = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    await _ghi_uy_quyen(
        session_factory,
        tenant_id=tenant_id,
        nguoi_nhan_id=user_id,
        nguoi_cap_id=nguoi_cap_id,
        cap_luc=cap_luc,
        thu_hoi_luc=cap_luc + timedelta(hours=1),
    )
    # Vẫn trong 24 giờ, nhưng đã rút ⇒ không còn gì để mượn.
    assert await guard.quyen_duoc_uy_quyen(tenant_id, user_id, cap_luc + timedelta(hours=2)) == (
        frozenset()
    )


async def test_uy_quyen_khong_theo_nguoi_sang_tenant_khac(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Ràng buộc ``tenant_id`` trong câu lọc — thừa về lý thuyết, có thật về hiệu lực.

    Cùng tinh thần ``TokenScopeGuard``: biến một tính chất của *một đường mã nguồn hôm nay*
    thành một **ràng buộc** áp cho mọi đường vào, kể cả đường chưa được viết.
    """
    guard = UyQuyenGuard(session_factory)
    tenant_id, user_id, nguoi_cap_id = await _dung_tenant_va_nguoi(session_factory)
    cap_luc = datetime(2026, 8, 3, 9, 0, tzinfo=UTC)
    await _ghi_uy_quyen(
        session_factory,
        tenant_id=tenant_id,
        nguoi_nhan_id=user_id,
        nguoi_cap_id=nguoi_cap_id,
        cap_luc=cap_luc,
    )
    trong_han = cap_luc + timedelta(hours=1)

    assert await guard.quyen_duoc_uy_quyen(tenant_id, user_id, trong_han) == _QUYEN
    assert await guard.quyen_duoc_uy_quyen(uuid4(), user_id, trong_han) == frozenset()


async def test_nguoi_khong_co_uy_quyen_nhan_tap_RONG(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Ca thường gặp nhất — gần như mọi request của gần như mọi người."""
    guard = UyQuyenGuard(session_factory)
    assert await guard.quyen_duoc_uy_quyen(uuid4(), uuid4()) == frozenset()
