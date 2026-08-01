"""End-to-end: the audit trail is queryable over HTTP by an authorised actor.

Runs without ``allow_dev_auth`` — real login, real bearer tokens — so the actions
these tests trigger are themselves the rows they then read back.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.audit import AuditAction, AuditLogger
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
    db_path = tmp_path / "audit_e2e.db"
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


def _make_cashier(client: TestClient, admin: Any, email: str) -> str:
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    cashier_role = next(r for r in roles if r["code"] == CASHIER)
    user_id: str = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": email, "password": STAFF_PASSWORD, "full_name": "Thu Ngân"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    return user_id


# --- access control on the trail itself -------------------------------------


def test_reading_the_trail_requires_a_token(client: TestClient) -> None:
    assert client.get("/api/v1/audit-logs").status_code == 401


def test_a_cashier_cannot_read_the_trail(client: TestClient) -> None:
    """audit.read is deliberately not in the cashier role: the trail names who
    touched patient data, so reading it is privileged in its own right."""
    admin = _login(client)
    _make_cashier(client, admin, "tn@bera.vn")
    staff = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    assert client.get("/api/v1/audit-logs", headers=_auth(staff)).status_code == 403


def test_a_branch_pharmacist_cannot_read_the_trail(client: TestClient) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    role = next(r for r in roles if r["code"] == BRANCH_PHARMACIST)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "ds@bera.vn", "password": STAFF_PASSWORD, "full_name": "Dược Sĩ"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": role["id"], "branch_id": admin["branch_id"]},
    )
    ds = _login(client, "ds@bera.vn", STAFF_PASSWORD)

    assert client.get("/api/v1/audit-logs", headers=_auth(ds)).status_code == 403


# --- the trail answers "who did what" ---------------------------------------


def test_admin_reads_back_their_own_login(client: TestClient) -> None:
    admin = _login(client)
    r = client.get("/api/v1/audit-logs", headers=_auth(admin))
    assert r.status_code == 200

    body = r.json()
    assert body["total"] >= 1
    logins = [i for i in body["items"] if i["action"] == AuditAction.LOGIN_SUCCESS]
    assert logins and logins[0]["actor_user_id"] == admin["user_id"]
    assert logins[0]["tenant_id"] == admin["tenant_id"]
    # The API layer fills the client IP; TestClient reports itself as testclient.
    assert "client_ip" in logins[0]["context"]


def test_administrative_actions_show_up_with_actor_and_target(client: TestClient) -> None:
    admin = _login(client)
    user_id = _make_cashier(client, admin, "tn2@bera.vn")

    body = client.get("/api/v1/audit-logs", headers=_auth(admin)).json()
    created = [i for i in body["items"] if i["action"] == AuditAction.USER_CREATED]
    granted = [i for i in body["items"] if i["action"] == AuditAction.ROLE_GRANTED]

    assert created and created[0]["target_id"] == user_id
    assert created[0]["actor_user_id"] == admin["user_id"]
    assert granted and granted[0]["target_type"] == "user_role"


def test_a_failed_login_is_visible_afterwards(client: TestClient) -> None:
    client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": "SaiMatKhau123"})
    admin = _login(client)

    body = client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin),
        params={"action": AuditAction.LOGIN_FAILED.value},
    ).json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == AuditAction.LOGIN_FAILED


# --- filtering and paging ---------------------------------------------------


def test_filter_by_actor(client: TestClient) -> None:
    admin = _login(client)
    user_id = _make_cashier(client, admin, "tn3@bera.vn")
    _login(client, "tn3@bera.vn", STAFF_PASSWORD)

    body = client.get(
        "/api/v1/audit-logs", headers=_auth(admin), params={"actor_user_id": user_id}
    ).json()
    assert body["total"] == 1
    assert body["items"][0]["action"] == AuditAction.LOGIN_SUCCESS
    assert body["items"][0]["actor_user_id"] == user_id


def test_filter_by_unknown_actor_returns_empty_not_error(client: TestClient) -> None:
    admin = _login(client)
    body = client.get(
        "/api/v1/audit-logs", headers=_auth(admin), params={"actor_user_id": str(uuid4())}
    ).json()
    assert (body["total"], body["items"]) == (0, [])


def test_filter_by_time_window(client: TestClient) -> None:
    admin = _login(client)
    future = client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin),
        params={"occurred_from": "2099-01-01T00:00:00Z"},
    ).json()
    assert future["total"] == 0

    past = client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin),
        params={"occurred_from": "2000-01-01T00:00:00Z"},
    ).json()
    assert past["total"] >= 1


def test_reversed_time_window_is_rejected(client: TestClient) -> None:
    admin = _login(client)
    r = client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin),
        params={
            "occurred_from": "2026-07-23T10:00:00Z",
            "occurred_to": "2026-07-23T09:00:00Z",
        },
    )
    assert r.status_code == 422


def test_paging_reports_a_stable_total(client: TestClient) -> None:
    admin = _login(client)
    _make_cashier(client, admin, "tn4@bera.vn")

    first = client.get("/api/v1/audit-logs", headers=_auth(admin), params={"limit": 1}).json()
    second = client.get(
        "/api/v1/audit-logs", headers=_auth(admin), params={"limit": 1, "offset": 1}
    ).json()

    assert first["total"] == second["total"] >= 3
    assert len(first["items"]) == len(second["items"]) == 1
    assert first["items"][0]["id"] != second["items"][0]["id"]


def test_limit_is_bounded(client: TestClient) -> None:
    admin = _login(client)
    assert (
        client.get("/api/v1/audit-logs", headers=_auth(admin), params={"limit": 5000}).status_code
        == 422
    )


def test_trail_is_read_only_over_http(client: TestClient) -> None:
    """No write verb is exposed — the endpoint cannot be used to forge history."""
    admin = _login(client)
    for verb in (client.post, client.put, client.patch, client.delete):
        assert verb("/api/v1/audit-logs", headers=_auth(admin)).status_code == 405
