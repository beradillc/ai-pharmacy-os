"""Uỷ quyền quản trị có thời hạn — use-case + kho lưu, trên phiên CSDL thật.

Chain chốt 2026-08-03. Xem ``docs/features/uy-quyen-quan-tri/01_DECISIONS.md``.

🔴 **Mệnh đề đắt nhất của tệp này không phải "cấp được uỷ quyền"** mà là *quản trị hệ thống
KHÔNG cấp được* — vì nếu tài khoản kỹ thuật tự mở quyền cho tài khoản kỹ thuật thì cả cơ chế
này chỉ còn là thủ tục. Xem :func:`test_quan_tri_he_thong_KHONG_tu_cap_duoc_uy_quyen`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from pharmacy_os.core.audit import AuditAction, AuditLogger
from pharmacy_os.core.context import RequestContext
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.errors import NotFoundError, PermissionDeniedError
from pharmacy_os.core.errors import ValidationError as AppValidationError
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.modules.iam.application import (
    AssignRoleInput,
    AuthService,
    BootstrapTenantInput,
    CreateUserInput,
    IamService,
    LoginInput,
    SessionOutput,
    UyQuyenService,
)
from pharmacy_os.modules.iam.domain import CHAIN_PHARMACIST, UyQuyenQuanTri
from tests.integration.conftest import _iam_repos

pytestmark = pytest.mark.anyio

ADMIN_PASSWORD = "MatKhauAdmin2026"
KY_THUAT_PASSWORD = "MatKhauKyThuat26"
CHU_CHUOI_PASSWORD = "MatKhauChuChuoi26"
LY_DO = "Sửa lỗi hoá đơn PO-0007 tính sai tiền thối cho khách"


@pytest.fixture
def uy_quyen_service(
    session_factory: async_sessionmaker[AsyncSession], event_bus: InMemoryEventBus
) -> UyQuyenService:
    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    return UyQuyenService(uow_factory, _iam_repos, AuditLogger(session_factory))


def _ctx_of(session: SessionOutput) -> RequestContext:
    return RequestContext(
        tenant_id=session.tenant_id,
        branch_id=session.branch_id,
        user_id=session.user_id,
        permissions=frozenset(session.permissions),
    )


@dataclass(frozen=True, slots=True)
class Canh:
    """Ba nhân vật thật của kịch bản, không ai trong số họ là ``uuid4()`` bịa ra."""

    admin: RequestContext
    """Quản trị hệ thống — **không** có ``iam.delegation.grant``."""

    chu_chuoi: RequestContext
    """Chủ chuỗi — người duy nhất cấp được."""

    ky_thuat_id: UUID
    """Tài khoản bảo trì, người nhận uỷ quyền."""


async def _dung_canh(iam_service: IamService, auth_service: AuthService) -> Canh:
    """Một tenant thật, ba tài khoản thật, ba lượt **đăng nhập thật**.

    🔴 **Chủ chuỗi phải là một USER CÓ THẬT, không phải một ``RequestContext`` bịa.** Bản
    đầu của tệp này dựng chủ chuỗi bằng ``user_id=uuid4()`` + tập quyền chép từ
    ``SYSTEM_ROLES_BY_CODE`` — và 6/11 test đỏ ngay lượt chạy đầu vì khoá ngoại
    ``nguoi_cap_id -> users.id`` từ chối một id không tồn tại. Ràng buộc CSDL bắt đúng thứ nó
    sinh ra để bắt: **không ghi được một dòng uỷ quyền do một người không có thật cấp**.

    Và quan trọng hơn: quyền của chủ chuỗi ở đây đến từ **đường cấp phát thật** (gán vai →
    đăng nhập → giải mã token), không phải từ hằng số tôi chép tay. Hai vế của mọi phép so
    bên dưới vì thế có hai nguồn (kỷ luật #23) — nếu vai ``chain_pharmacist`` một ngày mất
    ``iam.delegation.grant``, các test này đỏ, thay vì xanh vì đọc lại chính hằng số đã đổi.
    """
    await iam_service.bootstrap_tenant(
        BootstrapTenantInput(
            tenant_name="Nhà thuốc Bera",
            branch_code="HQ",
            branch_name="Chi nhánh chính",
            admin_email="admin@bera.vn",
            admin_full_name="Nguyễn Quản Trị",
            admin_password=ADMIN_PASSWORD,
        )
    )
    phien_admin = await auth_service.login(
        LoginInput(email="admin@bera.vn", password=ADMIN_PASSWORD)
    )
    ctx_admin = _ctx_of(phien_admin)

    ky_thuat = await iam_service.create_user(
        CreateUserInput(
            email="kythuat@bera.vn",
            full_name="Trần Bảo Trì",
            password=KY_THUAT_PASSWORD,
        ),
        ctx_admin,
    )

    chu = await iam_service.create_user(
        CreateUserInput(
            email="chuchuoi@bera.vn",
            full_name="Lê Chủ Chuỗi",
            password=CHU_CHUOI_PASSWORD,
        ),
        ctx_admin,
    )
    vai = next(r for r in await iam_service.list_roles(ctx_admin) if r.code == CHAIN_PHARMACIST)
    # branch_id bỏ trống = cấp chuỗi (Luật 44/2024 Điều 17a) — đúng phạm vi của vai này.
    await iam_service.assign_role(chu.id, AssignRoleInput(role_id=vai.id), ctx_admin)

    phien_chu = await auth_service.login(
        LoginInput(email="chuchuoi@bera.vn", password=CHU_CHUOI_PASSWORD)
    )
    return Canh(admin=ctx_admin, chu_chuoi=_ctx_of(phien_chu), ky_thuat_id=ky_thuat.id)


# --- phân quyền -------------------------------------------------------------


async def test_quan_tri_he_thong_KHONG_tu_cap_duoc_uy_quyen(
    iam_service: IamService, auth_service: AuthService, uy_quyen_service: UyQuyenService
) -> None:
    """🔴 Mệnh đề giữ cho cả cơ chế có nghĩa.

    Nếu tài khoản kỹ thuật cấp được uỷ quyền thì nó cấp cho **một tài khoản kỹ thuật khác**,
    và điều kiện Chain đặt ra — *"chủ chuỗi sẽ chịu trách nhiệm"* — không còn ai thực hiện.
    Luật "không tự uỷ quyền cho chính mình" **không** đóng đường này: nó chỉ so hai id, nên
    hai tài khoản quản trị cấp chéo cho nhau là hợp lệ với mọi luật domain.

    Ctx ở đây đến từ một lượt **đăng nhập thật** của tài khoản admin do bootstrap tạo ra —
    không phải một tập quyền tôi tự gõ.
    """
    canh = await _dung_canh(iam_service, auth_service)

    assert "iam.delegation.grant" not in canh.admin.permissions, (
        "Quyền cấp uỷ quyền KHÔNG được nằm trong vai quản trị hệ thống — xem "
        "system_roles._SYSTEM_ADMIN_PERMISSIONS."
    )
    with pytest.raises(PermissionDeniedError):
        await uy_quyen_service.cap(canh.ky_thuat_id, LY_DO, canh.admin)


async def test_quan_tri_he_thong_VAN_doc_duoc_so_uy_quyen(
    iam_service: IamService, auth_service: AuthService, uy_quyen_service: UyQuyenService
) -> None:
    """Không cấp được **không** có nghĩa là không nhìn thấy.

    Người bảo trì phải đọc được sổ để biết quyền mình đang dùng đến từ đâu và hết hạn lúc
    nào; giấu nó đi chỉ tạo ra một người dùng hệ thống mà không hiểu vì sao mình mất quyền
    giữa chừng.
    """
    canh = await _dung_canh(iam_service, auth_service)
    assert "iam.delegation.read" in canh.admin.permissions
    assert await uy_quyen_service.liet_ke(canh.admin) == []


# --- cấp --------------------------------------------------------------------


async def test_chu_chuoi_cap_duoc_va_KHONG_kem_quyen_ky_so(
    iam_service: IamService, auth_service: AuthService, uy_quyen_service: UyQuyenService
) -> None:
    """Đường dùng thật, đầu-cuối: chủ chuỗi mở quyền cho tài khoản kỹ thuật.

    Hai khẳng định đi cùng nhau có chủ đích: uỷ quyền **có** mở dữ liệu bệnh nhân (nếu không
    thì người bảo trì lại đi mở ``psql``, đúng thứ Chain bác), và nó **không** mang theo quyền
    ký sổ kiểm soát đặc biệt (tư cách chuyên môn không chuyển bằng một thao tác phần mềm).
    """
    canh = await _dung_canh(iam_service, auth_service)

    uq = await uy_quyen_service.cap(canh.ky_thuat_id, LY_DO, canh.chu_chuoi)

    assert "crm.sensitive.read" in uq.quyen, "Uỷ quyền phải mở được hồ sơ bệnh nhân"
    assert "compliance.ledger.sign" not in uq.quyen, "Quyền ký sổ KHÔNG bao giờ đi qua uỷ quyền"
    assert uq.het_han_luc - uq.cap_luc == timedelta(hours=24), "Chain chốt 24 giờ cố định"
    assert uq.ly_do == LY_DO


async def test_ly_do_hoi_hot_bi_tu_choi(
    iam_service: IamService, auth_service: AuthService, uy_quyen_service: UyQuyenService
) -> None:
    canh = await _dung_canh(iam_service, auth_service)
    with pytest.raises(AppValidationError, match="ít nhất"):
        await uy_quyen_service.cap(canh.ky_thuat_id, ".", canh.chu_chuoi)


async def test_khong_cap_cho_nguoi_cua_tenant_khac_bao_KHONG_TIM_THAY(
    iam_service: IamService, auth_service: AuthService, uy_quyen_service: UyQuyenService
) -> None:
    """Người lạ ⇒ *không tìm thấy*, không phải *bị từ chối*.

    Trả 403 ở đây sẽ biến endpoint thành một cách dò xem một id có tồn tại ở tenant khác hay
    không — cùng kỷ luật ``IamService._user_or_404``.
    """
    canh = await _dung_canh(iam_service, auth_service)
    with pytest.raises(NotFoundError):
        await uy_quyen_service.cap(uuid4(), LY_DO, canh.chu_chuoi)


# --- kho lưu: hiệu lực theo thời gian ---------------------------------------


async def test_loc_SQL_khop_luat_domain_con_hieu_luc(
    iam_service: IamService,
    auth_service: AuthService,
    uy_quyen_service: UyQuyenService,
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
) -> None:
    """🔴 Phép lọc ``WHERE`` của kho lưu phải nói **cùng một điều** với ``con_hieu_luc``.

    Hai bản cài đặt của cùng một luật, viết bằng hai ngôn ngữ, không trình biên dịch nào nối
    được — đúng hình dạng kỷ luật #22. Ở đây chúng được so với nhau trên **cùng một mốc thời
    gian**, và mệnh đề độc lập là: hàng đã hết hạn vẫn **còn trong bảng** (chỉ-ghi-thêm), chỉ
    là không còn *hiệu lực*.
    """
    canh = await _dung_canh(iam_service, auth_service)
    uq = await uy_quyen_service.cap(canh.ky_thuat_id, LY_DO, canh.chu_chuoi)

    async with SqlAlchemyUnitOfWork(session_factory, event_bus) as uow:
        repos = _iam_repos(uow)

        trong_han = uq.cap_luc + timedelta(hours=23, minutes=59)
        qua_han = uq.cap_luc + timedelta(hours=24, minutes=1)

        con = await repos.uy_quyen.list_con_hieu_luc(canh.ky_thuat_id, trong_han)
        het = await repos.uy_quyen.list_con_hieu_luc(canh.ky_thuat_id, qua_han)

        assert [u.id for u in con] == [uq.id], "SQL phải thấy nó còn sống trong hạn"
        assert het == [], "SQL phải thấy nó đã chết sau hạn"

        # Hai vế của phép so đến từ hai chỗ: một bên là SQL, một bên là luật domain thuần.
        doc_lai = await repos.uy_quyen.get(uq.id)
        assert doc_lai is not None, "Hết hạn KHÔNG được xoá hàng — nó là vết kiểm toán"
        assert doc_lai.con_hieu_luc(trong_han) is True
        assert doc_lai.con_hieu_luc(qua_han) is False


async def test_thu_hoi_lam_het_hieu_luc_ngay_va_KHONG_xoa_hang(
    iam_service: IamService,
    auth_service: AuthService,
    uy_quyen_service: UyQuyenService,
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
) -> None:
    canh = await _dung_canh(iam_service, auth_service)
    uq = await uy_quyen_service.cap(canh.ky_thuat_id, LY_DO, canh.chu_chuoi)

    await uy_quyen_service.thu_hoi(uq.id, canh.chu_chuoi)

    async with SqlAlchemyUnitOfWork(session_factory, event_bus) as uow:
        repos = _iam_repos(uow)
        ngay_sau = datetime.now(UTC) + timedelta(minutes=1)
        assert await repos.uy_quyen.list_con_hieu_luc(canh.ky_thuat_id, ngay_sau) == []
        con_hang = await repos.uy_quyen.get(uq.id)
        assert con_hang is not None, "Thu hồi là GHI MỐC, không phải DELETE"
        assert con_hang.thu_hoi_luc is not None

    # Rút hai lần: lần sau không được đẩy mốc về sau, và không sinh dòng audit thứ hai.
    with pytest.raises(AppValidationError, match="hết hiệu lực"):
        await uy_quyen_service.thu_hoi(uq.id, canh.chu_chuoi)


async def test_anh_chup_quyen_khong_doi_khi_vai_nguoi_cap_doi(
    iam_service: IamService,
    auth_service: AuthService,
    uy_quyen_service: UyQuyenService,
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: InMemoryEventBus,
) -> None:
    """Ảnh chụp: phạm vi đúng bằng thứ người cấp nhìn thấy lúc bấm nút.

    Suy lại từ vai lúc dùng ⇒ một lần nâng quyền cho chủ chuỗi sẽ âm thầm nới rộng **mọi** uỷ
    quyền đang mở. Ở đây: cấp với một tập hẹp, rồi đọc lại — tập phải y nguyên, không phình
    ra theo vai.
    """
    canh = await _dung_canh(iam_service, auth_service)
    hep = frozenset({"crm.read", "sales.read"})

    uq = await uy_quyen_service.cap(canh.ky_thuat_id, LY_DO, canh.chu_chuoi, quyen_yeu_cau=hep)

    async with SqlAlchemyUnitOfWork(session_factory, event_bus) as uow:
        doc_lai = await _iam_repos(uow).uy_quyen.get(uq.id)
    assert doc_lai is not None
    assert doc_lai.quyen == hep, "Ảnh chụp phải đúng bằng tập đã cấp, không suy lại theo vai"


async def test_khong_xin_duoc_thu_chinh_minh_khong_co(
    iam_service: IamService, auth_service: AuthService, uy_quyen_service: UyQuyenService
) -> None:
    """Luật 2 nhìn từ tầng use-case: chủ chuỗi không có ``iam.user.create``.

    Chọn đúng mã ấy vì nó là quyền **thật sự** vắng khỏi vai chủ chuỗi (đã kiểm bằng lệnh:
    admin hơn chủ chuỗi đúng 4 mã ``iam.*``), nên test này đo một chênh lệch có thật chứ
    không phải một mã bịa ra cho tiện.
    """
    canh = await _dung_canh(iam_service, auth_service)
    assert "iam.user.create" not in canh.chu_chuoi.permissions

    with pytest.raises(AppValidationError, match="không có"):
        await uy_quyen_service.cap(
            canh.ky_thuat_id, LY_DO, canh.chu_chuoi, quyen_yeu_cau=frozenset({"iam.user.create"})
        )


# --- vết kiểm toán ----------------------------------------------------------


async def test_cap_va_thu_hoi_deu_de_lai_vet_voi_ly_do(
    iam_service: IamService,
    auth_service: AuthService,
    uy_quyen_service: UyQuyenService,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Uỷ quyền mở cửa, nó **không** tắt camera — và chính nó cũng phải để lại vết.

    ``ly_do`` phải có mặt trong audit: nó không tồn tại ở đâu khác dưới dạng người đọc được,
    và là thứ người rà soát đọc trước tiên. Số quyền thì có, **danh sách mã thì không** — sổ
    audit không phải bản sao thứ hai của bảng nó đang canh.
    """
    from sqlalchemy import select

    from pharmacy_os.core.audit.models import AuditLogORM

    canh = await _dung_canh(iam_service, auth_service)
    uq = await uy_quyen_service.cap(canh.ky_thuat_id, LY_DO, canh.chu_chuoi)
    await uy_quyen_service.thu_hoi(uq.id, canh.chu_chuoi)

    async with session_factory() as session:
        rows = (
            (
                await session.execute(
                    select(AuditLogORM).where(AuditLogORM.target_type == "uy_quyen_quan_tri")
                )
            )
            .scalars()
            .all()
        )

    hanh_vi = {r.action for r in rows}
    assert AuditAction.ADMIN_DELEGATION_GRANTED in hanh_vi
    assert AuditAction.ADMIN_DELEGATION_REVOKED in hanh_vi

    cap_row = next(r for r in rows if r.action == AuditAction.ADMIN_DELEGATION_GRANTED)
    assert cap_row.context["ly_do"] == LY_DO
    assert cap_row.context["so_quyen"] == str(len(uq.quyen))
    assert "crm.sensitive.read" not in str(cap_row.context), (
        "Audit mang SỐ quyền, không mang danh sách mã — nếu không nó thành bản sao thứ hai "
        "của bảng uy_quyen_quan_tri_quyen"
    )


async def test_liet_ke_giu_ca_cai_da_het_han(
    iam_service: IamService, auth_service: AuthService, uy_quyen_service: UyQuyenService
) -> None:
    """Màn rà soát hỏi *"tháng qua ai được mở quyền"* — lọc hết hạn đi thì nó luôn nói "không
    ai", đúng lúc nó cần trả lời nhiều nhất."""
    canh = await _dung_canh(iam_service, auth_service)
    uq = await uy_quyen_service.cap(canh.ky_thuat_id, LY_DO, canh.chu_chuoi)
    await uy_quyen_service.thu_hoi(uq.id, canh.chu_chuoi)

    so: list[UyQuyenQuanTri] = await uy_quyen_service.liet_ke(canh.admin)
    assert [u.id for u in so] == [uq.id], "Đã rút vẫn phải còn trên sổ"
