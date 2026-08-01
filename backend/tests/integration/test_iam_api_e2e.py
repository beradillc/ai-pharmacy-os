"""End-to-end HTTP: real login, real bearer tokens, no dev-auth headers.

``allow_dev_auth`` is left **off** here on purpose — this is the first suite that
exercises the API the way production will, so a regression that reopens the header
fallback shows up as a failure rather than a silently passing test.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

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
from pharmacy_os.modules.iam.domain import BRANCH_PHARMACIST, CASHIER
from pharmacy_os.modules.iam.interface import build_repositories
from tests.conftest import urls_csdl_thu

ADMIN_EMAIL = "admin@bera.vn"
ADMIN_PASSWORD = "MatKhauAdmin2026"
STAFF_PASSWORD = "MatKhauNhanVien26"


async def _bootstrap(db_url: str) -> None:
    """Seed the tenant on its own engine and event loop.

    Done before the app exists rather than through its container: the fixture is
    synchronous, and reaching for the ambient event loop breaks as soon as an
    earlier test in the session has closed one.
    """
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
    db_path = tmp_path / "iam_e2e.db"
    _sync_url, _async_url = urls_csdl_thu(db_path)
    sync_engine = create_engine(_sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    db_url = _async_url
    asyncio.run(_bootstrap(db_url))

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=db_url),
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


# --- the dev-auth fallback is closed ----------------------------------------


def test_request_without_a_token_is_401(client: TestClient) -> None:
    r = client.get("/api/v1/drugs")
    assert r.status_code == 401
    assert r.json()["type"].endswith("/unauthenticated")


def test_dev_headers_alone_do_not_authenticate(client: TestClient) -> None:
    """The old X-Tenant-Id/X-User-Id path must be inert with the flag off."""
    r = client.get(
        "/api/v1/drugs",
        headers={"X-Tenant-Id": str(uuid4()), "X-Branch-Id": str(uuid4())},
    )
    assert r.status_code == 401


# --- login ------------------------------------------------------------------


def test_login_returns_a_usable_token(client: TestClient) -> None:
    session = _login(client)
    assert session["token_type"] == "bearer"
    assert session["expires_in"] == 3600
    assert [b["code"] for b in session["accessible_branches"]] == ["HQ"]

    me = client.get("/api/v1/auth/me", headers=_auth(session))
    assert me.status_code == 200
    assert me.json()["user_id"] == session["user_id"]
    assert me.json()["branch_id"] == session["branch_id"]


def test_me_carries_the_name_and_email_the_screen_shows(client: TestClient) -> None:
    """``/auth/me`` phải trả **tên và email**, không chỉ định danh (M-03, UAT 01/08).

    🔴 Vì sao đáng một test riêng: nếu hai trường này biến mất, màn *Tài khoản của tôi*
    không đỏ ở đâu cả — nó hiện một khối hồ sơ **trống**, mà trống thì trông y hệt đang
    tải. Đường thay thế duy nhất là ``GET /users``, đòi ``iam.user.read`` — tức là **thu
    ngân không xem được tên của chính mình**. Test này canh đúng chỗ đó.
    """
    session = _login(client)
    me = client.get("/api/v1/auth/me", headers=_auth(session)).json()
    assert me["full_name"] == "Nguyễn Quản Trị"
    assert me["email"] == ADMIN_EMAIL
    # Cùng một sự thật, hai đường: `/auth/me` không được nói khác `/auth/login` về việc
    # tài khoản này còn nợ đổi mật khẩu hay không — màn Cài đặt và cửa chặn ở `AppShell`
    # đọc hai nguồn đó, và hai nguồn lệch nhau thì cửa chặn mở ra sai lúc.
    assert me["must_change_password"] == session["must_change_password"]
    # Vừa đăng nhập xong ⇒ phải có dấu thời gian. `None` ở đây nghĩa là màn sẽ hiện
    # "lần đầu" cho một người đã đăng nhập hàng trăm lần.
    assert me["last_login_at"] is not None


def test_a_staff_member_reads_their_own_name_without_iam_user_read(
    client: TestClient,
) -> None:
    """Thu ngân **không** có ``iam.user.read`` mà vẫn phải xem được hồ sơ của chính mình.

    Đây là toàn bộ lý do ``/auth/me`` được bổ sung thay vì màn đi vòng qua ``GET /users``:
    nếu test này đỏ thì thiết kế đã quay về đúng chỗ hỏng ban đầu.
    """
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    cashier_role = next(r for r in roles if r["code"] == CASHIER)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "tn9@bera.vn", "password": STAFF_PASSWORD, "full_name": "Thu Ngân 9"},
    ).json()["id"]
    # Chưa gán vai trò thì **không đăng nhập được** ("chưa được gán vai trò ở chi nhánh
    # nào") — nên phải gán trước, không phải bỏ qua bước này.
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    staff = _login(client, "tn9@bera.vn", STAFF_PASSWORD)
    assert "iam.user.read" not in staff["permissions"]
    assert client.get("/api/v1/users", headers=_auth(staff)).status_code == 403

    me = client.get("/api/v1/auth/me", headers=_auth(staff))
    assert me.status_code == 200
    assert me.json()["full_name"] == "Thu Ngân 9"


def test_wrong_password_is_401(client: TestClient) -> None:
    r = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "SaiMatKhau123"})
    assert r.status_code == 401


def test_a_real_token_reaches_a_business_endpoint(client: TestClient) -> None:
    session = _login(client)
    r = client.get("/api/v1/drugs", headers=_auth(session))
    assert r.status_code == 200


# --- the branch cannot be swapped by header (docs/15 §0 F1) -----------------


def test_x_branch_id_header_cannot_override_the_signed_branch(client: TestClient) -> None:
    session = _login(client)
    foreign_branch = str(uuid4())
    me = client.get(
        "/api/v1/auth/me",
        headers={**_auth(session), "X-Branch-Id": foreign_branch},
    )
    assert me.status_code == 200
    assert me.json()["branch_id"] == session["branch_id"] != foreign_branch


# --- user and role administration -------------------------------------------


def test_admin_creates_a_cashier_grants_a_branch_role_and_they_log_in(
    client: TestClient,
) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    cashier_role = next(r for r in roles if r["code"] == CASHIER)

    created = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={
            "email": "thu-ngan@bera.vn",
            "password": STAFF_PASSWORD,
            "full_name": "Trần Thu Ngân",
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]
    assert created.json()["must_change_password"] is True

    granted = client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    assert granted.status_code == 201
    assert granted.json()["role_code"] == CASHIER

    staff = _login(client, "thu-ngan@bera.vn", STAFF_PASSWORD)
    assert "sales.create" in staff["permissions"]
    # Legal boundaries from the seeded role survive all the way to the wire.
    assert "rx.dispense" not in staff["permissions"]
    # docs/15 §7n Q4 — cashier records the person and the consent, not the diagnoses.
    assert "crm.create" in staff["permissions"]
    assert "crm.sensitive.read" not in staff["permissions"]


def test_cashier_is_refused_a_pharmacist_only_endpoint(client: TestClient) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    cashier_role = next(r for r in roles if r["code"] == CASHIER)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "tn2@bera.vn", "password": STAFF_PASSWORD, "full_name": "Thu Ngân 2"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    staff = _login(client, "tn2@bera.vn", STAFF_PASSWORD)

    created = client.post("/api/v1/customers", headers=_auth(staff), json={"full_name": "Khách lẻ"})
    assert created.status_code == 201

    # crm.sensitive.write is deliberately absent from the cashier role (NĐ356 Điều 4.2):
    # recording an allergy is a pharmacist act, unlike creating the customer record.
    r = client.post(
        f"/api/v1/customers/{created.json()['id']}/allergies",
        headers=_auth(staff),
        json={"ingredient_id": str(uuid4()), "severity": "MILD"},
    )
    assert r.status_code == 403


def test_a_cashier_cannot_administer_users(client: TestClient) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    cashier_role = next(r for r in roles if r["code"] == CASHIER)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "tn3@bera.vn", "password": STAFF_PASSWORD, "full_name": "Thu Ngân 3"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    staff = _login(client, "tn3@bera.vn", STAFF_PASSWORD)

    assert client.get("/api/v1/users", headers=_auth(staff)).status_code == 403
    r = client.post(
        "/api/v1/users",
        headers=_auth(staff),
        json={"email": "x@bera.vn", "password": STAFF_PASSWORD, "full_name": "X"},
    )
    assert r.status_code == 403


def test_revoking_a_role_takes_effect_on_the_next_refresh(client: TestClient) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    pharmacist_role = next(r for r in roles if r["code"] == BRANCH_PHARMACIST)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "ds@bera.vn", "password": STAFF_PASSWORD, "full_name": "Dược Sĩ"},
    ).json()["id"]
    cashier_role = next(r for r in roles if r["code"] == CASHIER)
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    grant = client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": pharmacist_role["id"], "branch_id": admin["branch_id"]},
    ).json()

    staff = _login(client, "ds@bera.vn", STAFF_PASSWORD)
    assert "rx.dispense" in staff["permissions"]

    revoked = client.delete(f"/api/v1/users/{user_id}/roles/{grant['id']}", headers=_auth(admin))
    assert revoked.status_code == 204

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": staff["refresh_token"]})
    assert refreshed.status_code == 200
    # The cashier grant survives; only the pharmacist permissions are gone.
    assert "sales.create" in refreshed.json()["permissions"]
    assert "rx.dispense" not in refreshed.json()["permissions"]


# --- session lifecycle ------------------------------------------------------


def test_refresh_rotates_and_the_old_token_dies(client: TestClient) -> None:
    session = _login(client)
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != session["refresh_token"]

    replayed = client.post("/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert replayed.status_code == 401


def test_logout_then_refresh_is_401(client: TestClient) -> None:
    session = _login(client)
    assert (
        client.post(
            "/api/v1/auth/logout", json={"refresh_token": session["refresh_token"]}
        ).status_code
        == 204
    )
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": session["refresh_token"]})
    assert r.status_code == 401


def test_change_password_then_old_password_fails(client: TestClient) -> None:
    session = _login(client)
    r = client.post(
        "/api/v1/auth/change-password",
        headers=_auth(session),
        json={"current_password": ADMIN_PASSWORD, "new_password": "MatKhauMoi2026"},
    )
    assert r.status_code == 204

    assert (
        client.post(
            "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        ).status_code
        == 401
    )
    assert _login(client, ADMIN_EMAIL, "MatKhauMoi2026")["must_change_password"] is False


def test_short_password_is_rejected_by_the_schema(client: TestClient) -> None:
    admin = _login(client)
    r = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "yeu@bera.vn", "password": "ngan", "full_name": "Yếu"},
    )
    assert r.status_code == 422


def test_deactivating_a_user_blocks_their_next_login(client: TestClient) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    cashier_role = next(r for r in roles if r["code"] == CASHIER)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "nghi@bera.vn", "password": STAFF_PASSWORD, "full_name": "Nghỉ Việc"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    _login(client, "nghi@bera.vn", STAFF_PASSWORD)

    disabled = client.put(
        f"/api/v1/users/{user_id}/active", headers=_auth(admin), json={"active": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["status"] == "INACTIVE"

    r = client.post(
        "/api/v1/auth/login", json={"email": "nghi@bera.vn", "password": STAFF_PASSWORD}
    )
    assert r.status_code == 401


# --- F-9: giới hạn tần suất theo IP (kiểm toán B-10, C-11) ------------------


def test_a_burst_of_wrong_passwords_is_throttled_with_429(client: TestClient) -> None:
    """Bắn liên tục vào /auth/login từ một IP phải bị chặn bằng 429 kèm Retry-After.

    Mặc định là 10 lượt/phút, còn khoá tài khoản đứng ở 5 lần sai — nên tài khoản bị
    khoá **trước**, và những lượt sau đó tiếp tục đếm cho tới khi chạm hạn mức IP.
    """
    for _ in range(10):
        client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "sai-be-bet"})

    r = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "sai-be-bet"})
    assert r.status_code == 429, r.text
    assert int(r.headers["Retry-After"]) >= 1


def test_the_lockout_dos_vector_is_closed(client: TestClient) -> None:
    """Đây là **đúng lỗ hổng C-11**, viết thành một test đọc được.

    Khoá tài khoản mà không giới hạn IP nghĩa là kẻ tấn công khoá được **lần lượt từng
    tài khoản** của cả nhà thuốc mà không cần đoán trúng mật khẩu nào. Bắn vào nhiều
    tài khoản khác nhau vẫn phải chạm trần, vì bộ đếm khoá theo **(IP, endpoint)** chứ
    không theo tài khoản.
    """
    for i in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": f"nan-nhan-{i}@bera.vn", "password": "khong-can-dung"},
        )

    r = client.post(
        "/api/v1/auth/login",
        json={"email": "nan-nhan-moi@bera.vn", "password": "khong-can-dung"},
    )
    assert r.status_code == 429, "một IP bắn vào 10 tài khoản khác nhau vẫn lọt — C-11 chưa đóng"


def test_the_2fa_code_exchange_is_throttled_too(client: TestClient) -> None:
    """Mã TOTP chỉ 6 chữ số — bề mặt đoán mò hẹp hơn mật khẩu nhiều bậc.

    ⚠️ **Giới hạn đã biết, ghi ra chứ không giấu:** FastAPI kiểm tra hình dạng body
    **trước** khi vào handler, nên bộ đếm chỉ tính những request **đúng schema**. Bắn
    body sai hình dạng vẫn không bị tính — muốn chặn cả loại đó thì phải chuyển sang
    middleware, và đó là việc của F-13 (403/429 chạy trước 422), không phải F-9. Với
    tấn công đoán mã thật thì body luôn đúng hình dạng, nên hạn mức vẫn có tác dụng.
    """
    body = {"challenge_token": "khong-ton-tai", "code": "000000"}
    for _ in range(10):
        client.post("/api/v1/auth/2fa/login", json=body)
    r = client.post("/api/v1/auth/2fa/login", json=body)
    assert r.status_code == 429, r.text


def test_a_throttled_ip_does_not_lock_everyone_else_out(client: TestClient) -> None:
    """Hạn mức phải **mở lại được**, nếu không nó chỉ là một kiểu tự chặn mình.

    Reset bộ đếm mô phỏng "cửa sổ đã trôi qua" mà không phải chờ đồng hồ thật — cùng
    lý do các test đơn vị tiêm ``now`` thay vì ``sleep``.
    """
    for _ in range(11):
        client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "sai"})
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        ).status_code
        == 429
    )

    client.app.state.rate_limiter.reset()  # type: ignore[attr-defined]

    r = client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code != 429, "hết cửa sổ rồi mà vẫn chặn — hình phạt không có điểm kết thúc"


# --- B-07: token mang cặp tenant/chi nhánh lệch nhau -------------------------


def _forge(client: TestClient, *, tenant_id: str, branch_id: str, user_id: str) -> str:
    """Ký một token hợp lệ về CHỮ KÝ nhưng mang cặp tenant/chi nhánh không đi với nhau.

    Đúng cách kiểm toán B-07 dựng ra lỗ hổng. Cần secret ký, nên đây không phải kịch
    bản kẻ ngoài khai thác được — giá trị của test là chặn **một đường cấp token sai
    trong tương lai**, thứ không cần secret nào cả.
    """
    from pharmacy_os.core.security import JwtService
    from pharmacy_os.core.security.jwt import TokenPayload

    jwt_service: JwtService = client.app.state.container.resolve(JwtService)  # type: ignore[attr-defined]
    return jwt_service.issue(
        TokenPayload(
            user_id=UUID(user_id),
            tenant_id=UUID(tenant_id),
            branch_id=UUID(branch_id),
            permissions=frozenset({"catalog.read"}),
        )
    )


def test_token_with_branch_from_another_tenant_is_refused(client: TestClient) -> None:
    """Kiểm toán ghi được hàng tồn kho vào chi nhánh của tenant KHÁC và nhận 201.

    Điều làm nó nguy hiểm không phải khả năng khai thác (phải có secret ký) mà là hậu
    quả **không đảo ngược bằng git revert**: dòng dữ liệu lai tenant nằm im trong CSDL,
    không báo cáo nào hiển thị vì mọi báo cáo đều lọc theo chi nhánh người xem.
    """
    admin = _login(client)
    forged = _forge(
        client,
        tenant_id=admin["tenant_id"],
        branch_id=str(uuid4()),  # chi nhánh không thuộc tenant này (không tồn tại)
        user_id=admin["user_id"],
    )

    r = client.get("/api/v1/drugs", headers={"Authorization": f"Bearer {forged}"})

    assert r.status_code == 401, r.text


def test_a_genuine_token_still_works_after_the_guard(client: TestClient) -> None:
    """Mặt ngược lại — cổng phải MỞ ĐƯỢC. Một cổng chỉ biết từ chối thì không phải cổng."""
    admin = _login(client)

    r = client.get("/api/v1/drugs", headers=_auth(admin))

    assert r.status_code == 200, r.text


def test_token_whose_sub_belongs_to_another_tenant_is_refused(client: TestClient) -> None:
    """Kịch bản B-13: ``sub`` = người của tenant A, ``tenant``/``branch`` của tenant V.

    Kiểm toán gọi ``/auth/me`` bằng token đó và nhận **200**, rồi **đọc được người dùng
    của tenant nạn nhân**. Máy chủ chưa bao giờ kiểm lại rằng ``sub`` thuộc ``tenant``.

    Giá trị của bản vá không nằm ở việc chặn một kẻ tấn công — vẫn phải có secret ký.
    Nó nằm ở chỗ **định lượng lại bán kính của A-02**: trước đây lộ khoá ký = toàn quyền
    trên mọi tenant ngay lập tức, vì phía sau không còn lớp kiểm nào. Nay lộ khoá vẫn
    mất tất cả, **nhưng để lại dấu vết** — dòng log ``token_scope_mismatch``.
    """
    admin = _login(client)
    forged = _forge(
        client,
        tenant_id=admin["tenant_id"],
        branch_id=admin["branch_id"],
        user_id=str(uuid4()),  # người dùng không thuộc tenant này (không tồn tại)
    )

    r = client.get("/api/v1/drugs", headers={"Authorization": f"Bearer {forged}"})

    assert r.status_code == 401, r.text
