"""End-to-end HTTP for 2FA: real login, real bearer tokens, real TOTP codes.

Mirrors ``test_iam_api_e2e.py`` (dev-auth off, production shape). What this suite is
for, beyond "the endpoints respond": the two-step login must be **impossible to skip**.
A 2FA that can be walked around by calling a different endpoint is decoration, so the
bypass attempts here matter more than the happy path.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import (
    AppSettings,
    DatabaseSettings,
    SecuritySettings,
    Settings,
)
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.iam.application import BootstrapTenantInput, IamService
from pharmacy_os.modules.iam.domain import CASHIER
from pharmacy_os.modules.iam.interface import build_repositories

ADMIN_EMAIL = "admin@bera.vn"
ADMIN_PASSWORD = "MatKhauAdmin2026"
STAFF_PASSWORD = "MatKhauNhanVien26"

_LOGIN = "/api/v1/auth/login"
_LOGIN_2FA = "/api/v1/auth/2fa/login"
_ENROLL = "/api/v1/auth/2fa/enroll"
_ACTIVATE = "/api/v1/auth/2fa/activate"
_DISABLE = "/api/v1/auth/2fa/disable"
_STATUS = "/api/v1/auth/2fa"


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


def _build_client(tmp_path: Path, name: str) -> TestClient:
    db_path = tmp_path / f"{name}.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    db_url = f"sqlite+aiosqlite:///{db_path}"
    asyncio.run(_bootstrap(db_url))
    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=db_url),
        security=SecuritySettings(jwt_secret="test-secret-key-0123456789abcdef"),  # type: ignore[arg-type]
    )
    return TestClient(create_app(settings))


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with _build_client(tmp_path, "two_factor_e2e") as c:
        yield c


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD) -> Any:
    r = client.post(_LOGIN, json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(session: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def _code(secret: str, *, skew_seconds: int = 0) -> str:
    """A valid TOTP code; ``skew_seconds`` moves to a neighbouring step.

    Needed after a code has been spent: the replay watermark refuses any step at or
    below the last one used, so reusing "now" would (correctly) be rejected.
    """
    return str(pyotp.TOTP(secret).at(datetime.now(UTC) + timedelta(seconds=skew_seconds)))


def _enrol(client: TestClient, session: Any) -> tuple[str, list[str]]:
    """Enrol + activate for an already-logged-in session; returns secret and codes."""
    enrolled = client.post(_ENROLL, headers=_auth(session))
    assert enrolled.status_code == 200, enrolled.text
    secret = enrolled.json()["secret"]

    activated = client.post(_ACTIVATE, headers=_auth(session), json={"code": _code(secret)})
    assert activated.status_code == 200, activated.text
    return secret, activated.json()["backup_codes"]


# --- enrolment ----------------------------------------------------------------


def test_enrolment_returns_a_secret_and_a_provisioning_uri(client: TestClient) -> None:
    session = _login(client)
    r = client.post(_ENROLL, headers=_auth(session))

    assert r.status_code == 200
    body = r.json()
    assert body["secret"]
    # The URI is what a client turns into a QR code; it must carry the same secret.
    assert body["provisioning_uri"].startswith("otpauth://totp/")
    assert body["secret"] in body["provisioning_uri"]


def test_enrolment_alone_does_not_change_login(client: TestClient) -> None:
    """A secret that was never confirmed must not lock anybody out — the whole reason
    activation is a separate step."""
    session = _login(client)
    client.post(_ENROLL, headers=_auth(session))

    assert (
        client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).status_code
        == 200
    )


def test_activation_requires_a_correct_code(client: TestClient) -> None:
    session = _login(client)
    client.post(_ENROLL, headers=_auth(session))

    r = client.post(_ACTIVATE, headers=_auth(session), json={"code": "000000"})
    assert r.status_code == 401


def test_activation_hands_back_backup_codes_once(client: TestClient) -> None:
    session = _login(client)
    _, codes = _enrol(client, session)

    assert len(codes) == 10
    assert len(set(codes)) == 10  # distinct, not one code repeated
    # There is no endpoint that reads them back — status only reports how many remain.
    status = client.get(_STATUS, headers=_auth(session)).json()
    assert status["unused_backup_codes"] == 10
    assert status["active"] is True


# --- the two-step login -------------------------------------------------------


def test_login_with_2fa_active_returns_a_challenge_not_a_token(client: TestClient) -> None:
    session = _login(client)
    _enrol(client, session)

    r = client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})

    assert r.status_code == 401
    body = r.json()
    assert body["challenge_token"]
    # The half-finished login must not leak anything usable.
    assert "access_token" not in body
    assert "refresh_token" not in body


def test_the_challenge_plus_a_code_completes_the_login(client: TestClient) -> None:
    session = _login(client)
    secret, _ = _enrol(client, session)

    challenge = client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()
    r = client.post(
        _LOGIN_2FA,
        json={
            "challenge_token": challenge["challenge_token"],
            "code": _code(secret, skew_seconds=30),
        },
    )

    assert r.status_code == 200, r.text
    assert r.json()["access_token"]


def test_a_backup_code_also_completes_the_login(client: TestClient) -> None:
    """The lost-phone path: it must work, or 2FA gets switched off in practice."""
    session = _login(client)
    _, codes = _enrol(client, session)

    challenge = client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()
    r = client.post(
        _LOGIN_2FA, json={"challenge_token": challenge["challenge_token"], "code": codes[0]}
    )

    assert r.status_code == 200, r.text


def test_a_backup_code_cannot_be_used_twice(client: TestClient) -> None:
    session = _login(client)
    _, codes = _enrol(client, session)

    for expected in (200, 401):
        challenge = client.post(
            _LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        ).json()
        r = client.post(
            _LOGIN_2FA, json={"challenge_token": challenge["challenge_token"], "code": codes[0]}
        )
        assert r.status_code == expected


def test_a_wrong_code_does_not_complete_the_login(client: TestClient) -> None:
    session = _login(client)
    _enrol(client, session)

    challenge = client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()
    r = client.post(
        _LOGIN_2FA, json={"challenge_token": challenge["challenge_token"], "code": "000000"}
    )
    assert r.status_code == 401


def test_a_forged_challenge_is_refused(client: TestClient) -> None:
    """The token is opaque and server-side; guessing one must not authenticate."""
    session = _login(client)
    secret, _ = _enrol(client, session)

    r = client.post(_LOGIN_2FA, json={"challenge_token": "a" * 43, "code": _code(secret)})
    assert r.status_code == 401


def test_a_challenge_is_single_use(client: TestClient) -> None:
    session = _login(client)
    secret, _ = _enrol(client, session)

    challenge = client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()
    token = challenge["challenge_token"]
    first = client.post(
        _LOGIN_2FA, json={"challenge_token": token, "code": _code(secret, skew_seconds=30)}
    )
    assert first.status_code == 200

    replay = client.post(
        _LOGIN_2FA, json={"challenge_token": token, "code": _code(secret, skew_seconds=60)}
    )
    assert replay.status_code == 401


def test_five_wrong_codes_burn_the_challenge(client: TestClient) -> None:
    """A six-digit code is 10^6; without a cap, holding the password is enough."""
    session = _login(client)
    secret, _ = _enrol(client, session)

    challenge = client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).json()
    token = challenge["challenge_token"]
    for _ in range(5):
        assert (
            client.post(_LOGIN_2FA, json={"challenge_token": token, "code": "000000"}).status_code
            == 401
        )

    # Even the *right* code no longer works: the attacker must present the password again.
    r = client.post(
        _LOGIN_2FA, json={"challenge_token": token, "code": _code(secret, skew_seconds=30)}
    )
    assert r.status_code == 401


def test_a_wrong_password_never_reaches_the_second_step(client: TestClient) -> None:
    session = _login(client)
    _enrol(client, session)

    r = client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": "SaiMatKhau2026"})
    assert r.status_code == 401
    assert "challenge_token" not in r.json()


# --- switching it off ---------------------------------------------------------


def test_disabling_requires_both_factors(client: TestClient) -> None:
    """Password alone would let a stolen password remove the control that exists to
    protect against a stolen password."""
    session = _login(client)
    secret, _ = _enrol(client, session)

    wrong_code = client.post(
        _DISABLE,
        headers=_auth(session),
        json={"current_password": ADMIN_PASSWORD, "code": "000000"},
    )
    assert wrong_code.status_code == 401

    wrong_password = client.post(
        _DISABLE,
        headers=_auth(session),
        json={"current_password": "SaiMatKhau2026", "code": _code(secret, skew_seconds=30)},
    )
    assert wrong_password.status_code == 401

    assert client.get(_STATUS, headers=_auth(session)).json()["active"] is True


def test_disabling_with_both_factors_restores_single_step_login(client: TestClient) -> None:
    session = _login(client)
    secret, _ = _enrol(client, session)

    r = client.post(
        _DISABLE,
        headers=_auth(session),
        json={"current_password": ADMIN_PASSWORD, "code": _code(secret, skew_seconds=30)},
    )
    assert r.status_code == 204

    assert (
        client.post(_LOGIN, json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}).status_code
        == 200
    )


# --- access control -----------------------------------------------------------


def test_two_factor_endpoints_require_a_token(client: TestClient) -> None:
    assert client.post(_ENROLL).status_code == 401
    assert client.post(_ACTIVATE, json={"code": "123456"}).status_code == 401
    assert client.get(_STATUS).status_code == 401


def test_a_cashier_can_manage_their_own_two_factor(client: TestClient) -> None:
    """2FA is not gated on a permission: anybody may protect their own account, and
    the enforcement flag only decides who is *compelled* to."""
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    role = next(r for r in roles if r["code"] == CASHIER)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "tn@bera.vn", "password": STAFF_PASSWORD, "full_name": "Thu Ngân"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": role["id"], "branch_id": admin["branch_id"]},
    )
    cashier = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    assert client.post(_ENROLL, headers=_auth(cashier)).status_code == 200


def test_an_admin_can_reset_another_users_two_factor(client: TestClient) -> None:
    admin = _login(client)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "ds@bera.vn", "password": STAFF_PASSWORD, "full_name": "Dược Sĩ"},
    ).json()["id"]

    r = client.post(
        f"/api/v1/users/{user_id}/2fa/reset",
        headers=_auth(admin),
        json={"current_password": ADMIN_PASSWORD},
    )
    assert r.status_code == 204


def test_a_cashier_cannot_reset_someone_elses_two_factor(client: TestClient) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    role = next(r for r in roles if r["code"] == CASHIER)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "tn2@bera.vn", "password": STAFF_PASSWORD, "full_name": "Thu Ngân"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": role["id"], "branch_id": admin["branch_id"]},
    )
    cashier = _login(client, "tn2@bera.vn", STAFF_PASSWORD)

    r = client.post(
        f"/api/v1/users/{user_id}/2fa/reset",
        headers=_auth(cashier),
        json={"current_password": STAFF_PASSWORD},
    )
    assert r.status_code == 403


# --- B-05: hạ phòng thủ của người khác phải qua chính cơ chế đó ---------------


def test_reset_two_factor_refuses_without_step_up(client: TestClient) -> None:
    """Chuỗi tấn công B-05 bắt đầu ở đây: chiếm một phiên ĐANG MỞ của tài khoản có
    `iam.user.write` (máy quầy bỏ trống) rồi gỡ 2FA của dược sĩ mà không phải chứng
    minh lại gì. Nay thân yêu cầu thiếu step-up ⇒ 422; sai mật khẩu ⇒ 403."""
    admin = _login(client)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "ds2@bera.vn", "password": STAFF_PASSWORD, "full_name": "Dược Sĩ"},
    ).json()["id"]

    no_body = client.post(f"/api/v1/users/{user_id}/2fa/reset", headers=_auth(admin))
    assert no_body.status_code == 422, no_body.text

    wrong = client.post(
        f"/api/v1/users/{user_id}/2fa/reset",
        headers=_auth(admin),
        json={"current_password": "SaiMatKhau2026"},
    )
    assert wrong.status_code == 403, wrong.text


def test_reset_password_refuses_without_step_up(client: TestClient) -> None:
    """Bước thứ hai của cùng chuỗi tấn công — gỡ 2FA xong thì đặt lại mật khẩu."""
    admin = _login(client)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "ds3@bera.vn", "password": STAFF_PASSWORD, "full_name": "Dược Sĩ"},
    ).json()["id"]

    wrong = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        headers=_auth(admin),
        json={"new_password": "MatKhauMoi2026", "current_password": "SaiMatKhau2026"},
    )
    assert wrong.status_code == 403, wrong.text

    ok = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        headers=_auth(admin),
        json={"new_password": "MatKhauMoi2026", "current_password": ADMIN_PASSWORD},
    )
    assert ok.status_code == 204, ok.text


def test_step_up_error_does_not_say_which_factor_failed(client: TestClient) -> None:
    """Người bấm hợp lệ biết mình vừa nhập gì; kẻ dò thì không nên được kể thêm."""
    admin = _login(client)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "ds4@bera.vn", "password": STAFF_PASSWORD, "full_name": "Dược Sĩ"},
    ).json()["id"]

    r = client.post(
        f"/api/v1/users/{user_id}/2fa/reset",
        headers=_auth(admin),
        json={"current_password": "SaiMatKhau2026"},
    )

    detail = r.json()["detail"].lower()
    assert "mật khẩu" in detail and "mã 2fa" in detail  # nói cần cả hai, không nói cái nào sai
