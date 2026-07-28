"""Ràng buộc các claim trong token phải đi được với nhau — đóng audit B-07 và B-13.

**Lỗ hổng.** Kiểm toán 2026-07-26 dựng một token ký `tenant=A` + `branch=` chi nhánh
của tenant V, rồi **ghi được hàng tồn kho vào chi nhánh lạ** (201). Ba tầng đều không
chặn: CSDL không có FK trên ``branch_id``; repository lọc theo cả hai cột nhưng **coi cả
hai là dữ liệu đầu vào tin cậy**; ``get_context`` không kiểm lại quan hệ sau khi giải mã.

**Điều làm nó nguy hiểm không phải khả năng khai thác** — token phải được ký, nên cần
secret. Điều nguy hiểm là **hậu quả không đảo ngược được bằng ``git revert``**: nó để
lại hàng dữ liệu lai tenant nằm im trong CSDL, **không báo cáo nào hiển thị** (mọi báo
cáo lọc theo chi nhánh của người xem) và không cơ chế toàn vẹn nào phát hiện.

**B-13 là cùng một lỗ, nhìn từ phía ``sub``.** Kiểm toán ký token có ``sub`` = admin của
tenant A nhưng ``tenant``/``branch`` của tenant V, gọi ``/auth/me`` ⇒ **200**, rồi **đọc
được người dùng của tenant V**. Máy chủ chưa bao giờ kiểm lại rằng ``sub`` thuộc
``tenant``. Giá trị của phát hiện không nằm ở khả năng khai thác (vẫn cần secret ký) mà
ở chỗ nó **định lượng bán kính của A-02**: khoá ký lộ không chỉ là giả mạo đăng nhập, mà
là **toàn quyền trên mọi tenant ngay lập tức**, vì phía sau không còn lớp kiểm nào.
Thêm kiểm tra này biến *"lộ khoá = mất tất cả"* thành *"lộ khoá = mất tất cả **và** để
lại dấu vết bất thường"* — dòng log ``token_scope_mismatch``.

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


class TokenScopeGuard:
    """Xác nhận các claim trong token **đi được với nhau**, và nhớ kết quả đúng.

    Hai câu hỏi, hai cache riêng — vì chúng hỏi hai bảng khác nhau và một cặp hợp lệ ở
    câu này không nói gì về câu kia:

    * ``branch_belongs_to_tenant`` — đóng **B-07**;
    * ``user_belongs_to_tenant`` — đóng **B-13**.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._verified_branches: set[tuple[UUID, UUID]] = set()
        self._verified_users: set[tuple[UUID, UUID]] = set()

    async def branch_belongs_to_tenant(self, tenant_id: UUID, branch_id: UUID) -> bool:
        return await self._verify(self._verified_branches, _table("branches"), tenant_id, branch_id)

    async def user_belongs_to_tenant(self, tenant_id: UUID, user_id: UUID) -> bool:
        """Đóng B-13: ``sub`` có thật sự thuộc ``tenant`` không.

        🔴 **Câu này KHÔNG trả lời "người này còn hoạt động không".** Trạng thái tài
        khoản không được kiểm ở đây, và cũng chưa từng được kiểm mỗi request — quyền
        nằm sẵn trong token, nên vô hiệu hoá một tài khoản chỉ có hiệu lực khi token
        hết hạn (60 phút). Đó là đánh đổi đã ghi ở ``docs/15`` D2, **không** phải thứ
        guard này vừa làm tệ đi. Nói rõ để không ai đọc nhầm cache dưới đây thành một
        lỗ hổng thu hồi.
        """
        return await self._verify(self._verified_users, _table("users"), tenant_id, user_id)

    async def _verify(
        self,
        cache: set[tuple[UUID, UUID]],
        table: Table,
        tenant_id: UUID,
        row_id: UUID,
    ) -> bool:
        pair = (tenant_id, row_id)
        if pair in cache:
            return True

        # Truy vấn thô thay vì qua repository của iam: guard này chạy ở tầng
        # composition/API cho MỌI module, nên nó không được kéo theo cả một service.
        async with self._session_factory() as session:
            found = (
                await session.execute(
                    select(1)
                    .select_from(table)
                    .where(table.c.id == row_id, table.c.tenant_id == tenant_id)
                    .limit(1)
                )
            ).scalar_one_or_none()

        if found is None:
            # Cố ý KHÔNG cache kết quả phủ định — xem docstring module.
            return False
        cache.add(pair)
        return True


def _table(name: str) -> Table:
    """Bảng lấy từ metadata dùng chung.

    Nhập trong hàm chứ không ở đầu tệp: ``core`` **cấm** import ``modules`` (contract
    ``kernel-knows-no-business``). Ở đây chỉ cần *cái bảng*, và bảng nằm trong metadata
    của ``Base`` — không phải một khái niệm nghiệp vụ nào của ``iam``.
    """
    from pharmacy_os.core.db.base import Base

    return Base.metadata.tables[name]
