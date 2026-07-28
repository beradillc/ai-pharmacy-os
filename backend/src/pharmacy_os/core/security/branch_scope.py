"""Ràng buộc ``branch_id`` phải thuộc ``tenant_id`` — đóng audit B-07.

**Lỗ hổng.** Kiểm toán 2026-07-26 dựng một token ký `tenant=A` + `branch=` chi nhánh
của tenant V, rồi **ghi được hàng tồn kho vào chi nhánh lạ** (201). Ba tầng đều không
chặn: CSDL không có FK trên ``branch_id``; repository lọc theo cả hai cột nhưng **coi cả
hai là dữ liệu đầu vào tin cậy**; ``get_context`` không kiểm lại quan hệ sau khi giải mã.

**Điều làm nó nguy hiểm không phải khả năng khai thác** — token phải được ký, nên cần
secret. Điều nguy hiểm là **hậu quả không đảo ngược được bằng ``git revert``**: nó để
lại hàng dữ liệu lai tenant nằm im trong CSDL, **không báo cáo nào hiển thị** (mọi báo
cáo lọc theo chi nhánh của người xem) và không cơ chế toàn vẹn nào phát hiện.

**Vì sao vẫn vá dù đường cấp token đã đúng.** Đã kiểm: ``AuthService._load_access`` chỉ
liệt kê chi nhánh **trong tenant của người dùng**, và ``_choose_branch`` đòi chi nhánh
được yêu cầu nằm trong danh sách đó — nên một token **cấp hợp lệ** không thể mang cặp
lệch. Nhưng đó là một tính chất của *một đường mã nguồn hôm nay*, không phải một ràng
buộc. Guard này biến nó thành ràng buộc, áp cho **mọi** đường vào, kể cả đường chưa
được viết.

**Vì sao có cache.** Không có cache thì mỗi request tốn một truy vấn chỉ để hỏi lại một
sự thật gần như không bao giờ đổi. Cache theo *cặp đã xác nhận*, không theo *danh sách
chi nhánh*: một cặp hợp lệ thì vĩnh viễn hợp lệ (chi nhánh không đổi tenant), nên không
có ca cache trả lời sai kiểu "đã bị thu hồi". Cặp **không** hợp lệ thì **không bao giờ
được cache** — nếu không, một lần tra hụt do lỗi tạm thời sẽ tự khoá mình lại.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Table, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


class BranchScopeGuard:
    """Xác nhận một cặp ``(tenant_id, branch_id)`` là có thật, và nhớ kết quả đúng."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._verified: set[tuple[UUID, UUID]] = set()

    async def is_valid(self, tenant_id: UUID, branch_id: UUID) -> bool:
        pair = (tenant_id, branch_id)
        if pair in self._verified:
            return True

        # Truy vấn thô thay vì qua repository của iam: guard này chạy ở tầng
        # composition/API cho MỌI module, nên nó không được kéo theo cả một service.
        async with self._session_factory() as session:
            found = (
                await session.execute(
                    select(1)
                    .select_from(_branches_table())
                    .where(
                        _branches_table().c.id == branch_id,
                        _branches_table().c.tenant_id == tenant_id,
                    )
                    .limit(1)
                )
            ).scalar_one_or_none()

        if found is None:
            # Cố ý KHÔNG cache kết quả phủ định — xem docstring module.
            return False
        self._verified.add(pair)
        return True


def _branches_table() -> Table:
    """Bảng ``branches`` lấy từ metadata dùng chung.

    Nhập trong hàm chứ không ở đầu tệp: ``core`` **cấm** import ``modules`` (contract
    ``kernel-knows-no-business``). Ở đây chỉ cần *cái bảng*, và bảng nằm trong metadata
    của ``Base`` — không phải một khái niệm nghiệp vụ nào của ``iam``.
    """
    from pharmacy_os.core.db.base import Base

    return Base.metadata.tables["branches"]
