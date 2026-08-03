"""End-to-end: uỷ quyền quản trị đi hết đường HTTP thật, token thật, không dev-auth.

🔴 **Mệnh đề mà chỉ e2e chứng minh được, ba tầng dưới không:** một tài khoản kỹ thuật
**bị 403** khi đọc hồ sơ bệnh nhân, rồi **được 200 trên đúng request ấy** sau khi chủ chuỗi
uỷ quyền — **mà không đăng nhập lại**. Đó là cả lý do cơ chế này không nằm trong JWT, và nó
chỉ đo được khi có một token thật đi qua một tiến trình thật hai lần.

Test tầng service không thấy được điều đó: nó dựng ``RequestContext`` bằng tay, tức là tự
trả lời câu hỏi mà nó đang định hỏi (kỷ luật #23).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.iam.application import BootstrapTenantInput, IamService
from pharmacy_os.modules.iam.domain import CHAIN_PHARMACIST, WAREHOUSE
from pharmacy_os.modules.iam.interface import build_repositories
from tests.conftest import urls_csdl_thu

ADMIN_EMAIL = "admin@bera.vn"
ADMIN_PASSWORD = "MatKhauAdmin2026"
CHU_CHUOI_EMAIL = "chuchuoi@bera.vn"
CHU_CHUOI_PASSWORD = "MatKhauChuChuoi26"
LY_DO = "Sửa lỗi hoá đơn PO-0007 tính sai tiền thối cho khách"


async def _bootstrap(db_url: str) -> None:
    engine = build_engine(db_url)
    session_factory = build_sessionmaker(engine)
    event_bus = InMemoryEventBus()

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    service = IamService(uow_factory, build_repositories, AuditLogger(session_factory))
    try:
        await service.bootstrap_tenant(
            BootstrapTenantInput(
                tenant_name="Nhà thuốc Bera",
                branch_code="HQ",
                branch_name="Chi nhánh chính",
                admin_email=ADMIN_EMAIL,
                admin_full_name="Nguyễn Quản Trị",
                admin_password=ADMIN_PASSWORD,
            )
        )
    finally:
        await engine.dispose()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "uy_quyen_e2e.db"
    sync_url, async_url = urls_csdl_thu(db_path)
    sync_engine = create_engine(sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    asyncio.run(_bootstrap(async_url))

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=async_url),
        security=SecuritySettings(jwt_secret="test-secret-key-0123456789abcdef"),  # type: ignore[arg-type]
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD) -> Any:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(session: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def _tao_chu_chuoi(client: TestClient, admin: Any) -> Any:
    """Một tài khoản chủ chuỗi thật, gán vai thật, đăng nhập thật."""
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    vai = next(r for r in roles if r["code"] == CHAIN_PHARMACIST)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={
            "email": CHU_CHUOI_EMAIL,
            "password": CHU_CHUOI_PASSWORD,
            "full_name": "Lê Chủ Chuỗi",
        },
    ).json()["id"]
    # branch_id bỏ trống ⇒ cấp chuỗi (Luật 44/2024 Điều 17a).
    r = client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": vai["id"]},
    )
    assert r.status_code in (200, 201), r.text
    return _login(client, CHU_CHUOI_EMAIL, CHU_CHUOI_PASSWORD)


# --- phân quyền trên chính endpoint uỷ quyền --------------------------------


def test_khong_token_thi_401(client: TestClient) -> None:
    assert client.get("/api/v1/uy-quyen").status_code == 401


def test_quan_tri_he_thong_bi_403_khi_CAP(client: TestClient) -> None:
    """🔴 Mệnh đề giữ cho cả cơ chế có nghĩa, đo qua HTTP thật.

    Tài khoản admin ở đây là tài khoản do ``bootstrap_tenant`` tạo — quyền của nó đến từ
    đường cấp phát thật, không phải một tập tôi tự gõ.
    """
    admin = _login(client)
    r = client.post(
        "/api/v1/uy-quyen",
        headers=_auth(admin),
        json={"nguoi_nhan_id": admin["user_id"], "ly_do": LY_DO},
    )
    assert r.status_code == 403, r.text


def test_quan_tri_he_thong_VAN_doc_duoc_so(client: TestClient) -> None:
    admin = _login(client)
    r = client.get("/api/v1/uy-quyen", headers=_auth(admin))
    assert r.status_code == 200, r.text
    assert r.json() == []


def test_khong_tu_uy_quyen_cho_chinh_minh(client: TestClient) -> None:
    """Chủ chuỗi có quyền cấp, nhưng không cấp cho chính mình — 422, không phải 403.

    Hai mã khác nhau vì hai chuyện khác nhau: 403 là *"anh không được phép làm việc này"*,
    422 là *"việc này không hợp lệ"*. Trộn chúng lại thì người dùng không biết mình đang bị
    chặn vì thiếu quyền hay vì gõ sai.
    """
    admin = _login(client)
    chu = _tao_chu_chuoi(client, admin)
    r = client.post(
        "/api/v1/uy-quyen",
        headers=_auth(chu),
        json={"nguoi_nhan_id": chu["user_id"], "ly_do": LY_DO},
    )
    assert r.status_code == 422, r.text
    assert "chính mình" in r.text


def test_ly_do_qua_ngan_bi_422_ngay_o_bien(client: TestClient) -> None:
    admin = _login(client)
    chu = _tao_chu_chuoi(client, admin)
    r = client.post(
        "/api/v1/uy-quyen",
        headers=_auth(chu),
        json={"nguoi_nhan_id": admin["user_id"], "ly_do": "."},
    )
    assert r.status_code == 422, r.text


def test_xin_dich_danh_quyen_ky_so_bi_tu_choi_ON_AO(client: TestClient) -> None:
    """Không lọc im lặng: người gõ tên quyền ký sổ vào đây phải biết là nó bị từ chối,
    chứ không phải tưởng mình vừa cấp được."""
    admin = _login(client)
    chu = _tao_chu_chuoi(client, admin)
    r = client.post(
        "/api/v1/uy-quyen",
        headers=_auth(chu),
        json={
            "nguoi_nhan_id": admin["user_id"],
            "ly_do": LY_DO,
            "quyen_yeu_cau": ["crm.read", "compliance.ledger.sign"],
        },
    )
    assert r.status_code == 422, r.text
    assert "Chứng chỉ hành nghề" in r.text


# --- 🔴 mệnh đề trung tâm ----------------------------------------------------


def test_uy_quyen_mo_quyen_NGAY_tren_token_CU_roi_rut_lai_cung_the(client: TestClient) -> None:
    """🔴 Đây là test đắt nhất của cả tính năng — và chỉ e2e đo được nó.

    Ba lượt gọi **cùng một token**, không đăng nhập lại giữa chừng:

    1. tài khoản kỹ thuật gọi một endpoint cần quyền nó không có ⇒ **403**;
    2. chủ chuỗi uỷ quyền ⇒ **cùng token ấy** gọi lại ⇒ **200**;
    3. chủ chuỗi rút ⇒ **cùng token ấy** gọi lại ⇒ **403**.

    Nếu quyền uỷ quyền nằm trong JWT thì bước 2 sẽ vẫn 403 (token cũ không có quyền mới) và
    bước 3 sẽ vẫn 200 (token cũ vẫn mang quyền đã rút) — **cả hai đều sai, theo hai hướng
    ngược nhau**. Chính vì thế cưỡng chế phải ở tầng request.
    """
    admin = _login(client)
    chu = _tao_chu_chuoi(client, admin)

    # Tài khoản bảo trì: có vai để đăng nhập được, nhưng KHÔNG có `crm.read`.
    #
    # 🔴 Vì sao phải gán một vai chứ không để trống: `/auth/login` từ chối tài khoản chưa
    # được gán vai ở chi nhánh nào ("Tài khoản chưa được gán vai trò ở chi nhánh nào") —
    # đo thật, bản đầu của test này đỏ đúng ở đó. Hành vi ấy của sản phẩm là đúng, nên test
    # phải dựng cảnh cho khớp thực tế thay vì đòi sản phẩm nới ra.
    #
    # Chọn `warehouse` vì đã kiểm bằng lệnh: nó là vai duy nhất KHÔNG có `crm.read`
    # (`cashier` thì CÓ). Bộ quyền bảo trì riêng (`maint.*`, Bước 2 của bản thiết kế) chưa
    # được xây, nên hôm nay đây là vai gần nhất với "kỹ thuật, không chạm dữ liệu bệnh nhân".
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    vai_kho = next(r for r in roles if r["code"] == WAREHOUSE)
    ky_thuat_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={
            "email": "kythuat@bera.vn",
            "password": "MatKhauKyThuat26",
            "full_name": "Trần Bảo Trì",
        },
    ).json()["id"]
    client.post(
        f"/api/v1/users/{ky_thuat_id}/roles",
        headers=_auth(admin),
        json={"role_id": vai_kho["id"], "branch_id": admin["branch_id"]},
    )
    ky_thuat = _login(client, "kythuat@bera.vn", "MatKhauKyThuat26")
    token_cu = _auth(ky_thuat)

    # ① chưa được uỷ quyền ⇒ 403
    truoc = client.get("/api/v1/customers", headers=token_cu)
    assert truoc.status_code == 403, truoc.text

    # ② chủ chuỗi uỷ quyền
    cap = client.post(
        "/api/v1/uy-quyen",
        headers=_auth(chu),
        json={"nguoi_nhan_id": ky_thuat_id, "ly_do": LY_DO},
    )
    assert cap.status_code == 201, cap.text
    uq = cap.json()
    assert uq["con_hieu_luc"] is True
    assert "compliance.ledger.sign" not in uq["quyen"], "Quyền ký KHÔNG đi qua uỷ quyền"
    assert "crm.read" in uq["quyen"]

    # CÙNG token cũ, không đăng nhập lại ⇒ 200
    trong = client.get("/api/v1/customers", headers=token_cu)
    assert trong.status_code == 200, (
        f"Uỷ quyền phải có hiệu lực NGAY trên token cũ, nhận {trong.status_code}. "
        "403 ở đây nghĩa là quyền mượn không được cộng ở tầng request."
    )

    # ③ rút ⇒ cùng token ấy mất quyền ngay
    rut = client.delete(f"/api/v1/uy-quyen/{uq['id']}", headers=_auth(chu))
    assert rut.status_code == 204, rut.text

    sau = client.get("/api/v1/customers", headers=token_cu)
    assert sau.status_code == 403, (
        f"Rút uỷ quyền phải có hiệu lực NGAY, nhận {sau.status_code}. 200 ở đây nghĩa là "
        "quyền đã rút vẫn sống trong token — đúng lỗi mà việc không-nhét-vào-JWT phải tránh."
    )


def test_rut_roi_van_con_tren_so_va_rut_lan_hai_bi_tu_choi(client: TestClient) -> None:
    """Sổ giữ cả cái đã rút: *"tháng qua ai được mở quyền"* phải trả lời được."""
    admin = _login(client)
    chu = _tao_chu_chuoi(client, admin)
    uq = client.post(
        "/api/v1/uy-quyen",
        headers=_auth(chu),
        json={"nguoi_nhan_id": admin["user_id"], "ly_do": LY_DO},
    ).json()

    assert client.delete(f"/api/v1/uy-quyen/{uq['id']}", headers=_auth(chu)).status_code == 204
    lai = client.delete(f"/api/v1/uy-quyen/{uq['id']}", headers=_auth(chu))
    assert lai.status_code == 422, lai.text

    so = client.get("/api/v1/uy-quyen", headers=_auth(admin)).json()
    assert [u["id"] for u in so] == [uq["id"]], "Đã rút vẫn phải còn trên sổ"
    assert so[0]["con_hieu_luc"] is False
    assert so[0]["thu_hoi_luc"] is not None
