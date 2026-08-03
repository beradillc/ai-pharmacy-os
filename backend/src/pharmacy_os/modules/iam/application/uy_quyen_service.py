"""Uỷ quyền quản trị có thời hạn — use-case (Chain chốt 2026-08-03).

Xem ``docs/features/uy-quyen-quan-tri/01_DECISIONS.md``. Tách khỏi :class:`IamService` vì
ba lý do, không phải vì tệp kia dài:

1. **Quyền gác khác nhau.** ``IamService`` gác bằng ``iam.user.*``/``iam.role.*`` — bộ
   quyền mà vai quản trị hệ thống **có đủ**. Uỷ quyền gác bằng ``iam.delegation.grant``,
   quyền **duy nhất** vai ấy không có (xem ``system_roles._SYSTEM_ADMIN_PERMISSIONS``).
   Để chung một lớp thì ranh giới ấy chỉ còn nằm trong trí nhớ người đọc.
2. **Đường đọc là đường nóng.** Bước 4/5 sẽ đọc uỷ quyền còn hiệu lực trên **mỗi request
   đã xác thực**. Đường ấy không được kéo theo cả một service quản trị người dùng.
3. Vòng đời của nó là **thời gian**, không phải trạng thái do người sửa.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pharmacy_os.core.audit import AuditAction, AuditEntry, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.errors import NotFoundError
from pharmacy_os.core.errors import ValidationError as AppValidationError
from pharmacy_os.core.security import require_permission
from pharmacy_os.modules.iam.application.repositories import ReposFactory, UowFactory
from pharmacy_os.modules.iam.domain import (
    UyQuyenKhongHopLe,
    UyQuyenQuanTri,
    tao_uy_quyen,
)


class UyQuyenService:
    def __init__(
        self,
        uow_factory: UowFactory,
        repos_factory: ReposFactory,
        audit: AuditLogger,
    ) -> None:
        self._uow_factory = uow_factory
        self._repos_factory = repos_factory
        self._audit = audit

    async def cap(
        self,
        nguoi_nhan_id: UUID,
        ly_do: str,
        ctx: RequestContext,
        *,
        quyen_yeu_cau: frozenset[str] | None = None,
    ) -> UyQuyenQuanTri:
        """Chủ chuỗi mở quyền nghiệp vụ cho một tài khoản, 24 giờ.

        🔴 **Phạm vi lấy từ ``ctx.permissions``, không đọc lại vai người cấp từ CSDL.**
        Đó chính là *"thứ người cấp nhìn thấy lúc bấm nút"* — mà ảnh chụp phải đúng bằng
        thứ ấy (xem ghi chú đầu ``domain/delegation.py``). Đọc lại vai lúc ghi sẽ mở một
        khe: vai vừa được nâng giữa lúc mở màn hình và lúc bấm nút thì người cấp cho đi
        nhiều hơn thứ họ vừa đọc trên màn.

        Kèm theo, ``ctx.permissions`` đã được thu hẹp theo **chi nhánh đang thao tác**, nên
        một người chỉ có quyền ở một chi nhánh không uỷ quyền ra phạm vi rộng hơn mình.
        """
        require_permission(ctx, "iam.delegation.grant")

        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            nguoi_nhan = await repos.users.get(nguoi_nhan_id)
            # Cùng kỷ luật ``IamService._user_or_404``: người thuộc tenant khác báo là
            # **không tìm thấy**, không phải "bị từ chối" — nếu không, endpoint này thành
            # một cách dò xem một id có tồn tại ở deployment khác hay không.
            if nguoi_nhan is None or nguoi_nhan.tenant_id != ctx.tenant_id:
                raise NotFoundError("Không tìm thấy người dùng")

            try:
                uy_quyen = tao_uy_quyen(
                    tenant_id=ctx.tenant_id,
                    nguoi_nhan_id=nguoi_nhan_id,
                    nguoi_cap_id=ctx.user_id,
                    ly_do=ly_do,
                    quyen_nguoi_cap=frozenset(ctx.permissions),
                    quyen_yeu_cau=quyen_yeu_cau,
                )
            except UyQuyenKhongHopLe as loi:
                raise AppValidationError(str(loi)) from loi

            await repos.uy_quyen.add(uy_quyen)
            await uow.commit()

        # ``context`` mang SỐ quyền, không mang danh sách mã: danh sách đầy đủ đã nằm ở
        # ``uy_quyen_quan_tri_quyen``, chép lại vào đây là biến sổ audit thành bản sao thứ
        # hai của bảng nó đang canh. ``ly_do`` thì có — nó không tồn tại ở đâu khác dưới
        # dạng người đọc được, và là thứ người rà soát đọc trước tiên.
        await self._record(
            ctx,
            AuditAction.ADMIN_DELEGATION_GRANTED,
            str(uy_quyen.id),
            nguoi_nhan_id=str(nguoi_nhan_id),
            so_quyen=str(len(uy_quyen.quyen)),
            ly_do=uy_quyen.ly_do,
            het_han_luc=uy_quyen.het_han_luc.isoformat(),
        )
        return uy_quyen

    async def thu_hoi(self, uy_quyen_id: UUID, ctx: RequestContext) -> None:
        """Rút một uỷ quyền **trước hạn** — hành vi có chủ ý, tách khỏi việc hết hạn.

        Không đòi người thu hồi phải là chính người đã cấp: nếu người cấp đi vắng thì một
        uỷ quyền đang mở phải rút được, còn *ai* rút thì đã có dòng audit trả lời.
        """
        require_permission(ctx, "iam.delegation.grant")
        bay_gio = datetime.now(UTC)

        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            uy_quyen = await repos.uy_quyen.get(uy_quyen_id)
            if uy_quyen is None or uy_quyen.tenant_id != ctx.tenant_id:
                raise NotFoundError("Không tìm thấy uỷ quyền")
            if not uy_quyen.con_hieu_luc(bay_gio):
                # Đã hết hạn hoặc đã rút: không phải lỗi của người bấm, nhưng cũng không
                # được ghi thêm một dòng audit "đã rút" cho một thứ vốn không còn hiệu lực
                # — sổ sẽ đọc như thể vừa có gì đó bị lấy đi.
                raise AppValidationError("Uỷ quyền này đã hết hiệu lực")
            await repos.uy_quyen.thu_hoi(uy_quyen_id, bay_gio)
            await uow.commit()

        await self._record(
            ctx,
            AuditAction.ADMIN_DELEGATION_REVOKED,
            str(uy_quyen_id),
            nguoi_nhan_id=str(uy_quyen.nguoi_nhan_id),
            con_lai_phut=str(int((uy_quyen.het_han_luc - bay_gio).total_seconds() // 60)),
        )

    async def liet_ke(
        self, ctx: RequestContext, *, limit: int = 50, offset: int = 0
    ) -> list[UyQuyenQuanTri]:
        """Sổ uỷ quyền của tenant, mới nhất trước — **cả những cái đã hết hạn**.

        Hết hạn không bị lọc khỏi màn: câu hỏi người rà soát hỏi là *"tháng qua ai được mở
        quyền đọc hồ sơ bệnh nhân"*, và một màn chỉ hiện cái đang mở sẽ luôn trả lời
        *"không ai"* — đúng lúc nó cần trả lời nhiều nhất.
        """
        require_permission(ctx, "iam.delegation.read")
        async with self._uow_factory() as uow:
            repos = self._repos_factory(uow)
            return await repos.uy_quyen.list_cua_tenant(ctx.tenant_id, limit=limit, offset=offset)

    async def _record(
        self, ctx: RequestContext, action: AuditAction, target_id: str, **extra: str
    ) -> None:
        await self._audit.record(
            AuditEntry(
                actor_user_id=ctx.user_id,
                tenant_id=ctx.tenant_id,
                action=action,
                # Chuỗi VIẾT THẲNG, không qua hằng số — cố ý. Cổng bắt chéo hai ngôn ngữ
                # (`nhat-ky/nhan-hanh-vi.test.ts`) quét `target_type="..."` trong mã nguồn
                # Python để đối chiếu với bảng nhãn TS. Một hằng số `_TARGET` làm phép quét
                # ấy **không thấy** loại này ⇒ tự ý bước ra ngoài cổng của kỷ luật #22, và
                # mã máy sẽ lọt ra giữa tiếng Việt trên màn nhật ký mà không cổng nào đỏ.
                # Đã đo thật: bản dùng hằng số làm cổng đỏ ở chiều "nhãn thừa".
                target_type="uy_quyen_quan_tri",
                target_id=target_id,
            ).with_context(**ctx.audit_meta, branch_id=str(ctx.branch_id), **extra)
        )
