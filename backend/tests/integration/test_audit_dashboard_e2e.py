"""End-to-end: the audit **dashboard** — its own permission, entity filter, CSV export.

Runs without ``allow_dev_auth`` (real login, real bearer tokens), so the actions
these tests trigger are themselves the rows the dashboard reads back. Complements
``test_audit_api_e2e`` (the raw ``/audit-logs`` query): the point here is what the
dashboard adds — ``audit.dashboard.read`` as a distinct grant a branch manager holds,
the ``target_type`` filter, and the CSV export.
"""

from __future__ import annotations

import asyncio
import csv
import io
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.audit import AuditAction, AuditLogger
from pharmacy_os.core.audit.csv_export import CSV_HEADER
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

_DASHBOARD = "/api/v1/audit-dashboard"


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
    db_path = tmp_path / "audit_dashboard_e2e.db"
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


def _make_staff(client: TestClient, admin: Any, email: str, role_code: str) -> str:
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    role = next(r for r in roles if r["code"] == role_code)
    user_id: str = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": email, "password": STAFF_PASSWORD, "full_name": "Nhân Viên"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": role["id"], "branch_id": admin["branch_id"]},
    )
    return user_id


# --- access control: a distinct permission ----------------------------------


def test_dashboard_requires_a_token(client: TestClient) -> None:
    assert client.get(_DASHBOARD).status_code == 401
    assert client.get(f"{_DASHBOARD}/export").status_code == 401


def test_a_cashier_cannot_open_the_dashboard(client: TestClient) -> None:
    admin = _login(client)
    _make_staff(client, admin, "tn@bera.vn", CASHIER)
    staff = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    assert client.get(_DASHBOARD, headers=_auth(staff)).status_code == 403
    assert client.get(f"{_DASHBOARD}/export", headers=_auth(staff)).status_code == 403


def test_a_branch_pharmacist_can_open_the_dashboard(client: TestClient) -> None:
    """The dashboard's whole point: a branch manager gets this lens via
    audit.dashboard.read even though they cannot use the raw /audit-logs query
    (which needs audit.read — see test_audit_api_e2e)."""
    admin = _login(client)
    _make_staff(client, admin, "ds@bera.vn", BRANCH_PHARMACIST)
    ds = _login(client, "ds@bera.vn", STAFF_PASSWORD)

    assert client.get(_DASHBOARD, headers=_auth(ds)).status_code == 200
    # ...and is still refused the raw query, proving the two permissions are separate.
    assert client.get("/api/v1/audit-logs", headers=_auth(ds)).status_code == 403


# --- the entity (target_type) filter the raw query never had ----------------


def test_filter_by_target_type(client: TestClient) -> None:
    admin = _login(client)
    _make_staff(client, admin, "tn2@bera.vn", CASHIER)

    role_grants = client.get(
        _DASHBOARD, headers=_auth(admin), params={"target_type": "user_role"}
    ).json()
    assert role_grants["total"] >= 1
    assert {i["target_type"] for i in role_grants["items"]} == {"user_role"}
    assert all(i["action"] == AuditAction.ROLE_GRANTED for i in role_grants["items"])

    users = client.get(_DASHBOARD, headers=_auth(admin), params={"target_type": "user"}).json()
    assert users["total"] >= 1
    assert "user_role" not in {i["target_type"] for i in users["items"]}


def test_unknown_target_type_returns_empty_not_error(client: TestClient) -> None:
    admin = _login(client)
    body = client.get(
        _DASHBOARD, headers=_auth(admin), params={"target_type": "does_not_exist"}
    ).json()
    assert (body["total"], body["items"]) == (0, [])


def test_reversed_time_window_is_rejected(client: TestClient) -> None:
    admin = _login(client)
    r = client.get(
        _DASHBOARD,
        headers=_auth(admin),
        params={
            "occurred_from": "2026-07-24T10:00:00Z",
            "occurred_to": "2026-07-24T09:00:00Z",
        },
    )
    assert r.status_code == 422


# --- CSV export -------------------------------------------------------------


def test_export_returns_csv_with_header_and_rows(client: TestClient) -> None:
    admin = _login(client)
    _make_staff(client, admin, "tn3@bera.vn", CASHIER)

    r = client.get(f"{_DASHBOARD}/export", headers=_auth(admin))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(r.text)))
    assert tuple(rows[0]) == CSV_HEADER
    assert len(rows) > 1  # header + at least the login/user-create/role-grant facts
    actions = {row[CSV_HEADER.index("action")] for row in rows[1:]}
    assert AuditAction.USER_CREATED.value in actions


def test_export_respects_the_target_type_filter(client: TestClient) -> None:
    admin = _login(client)
    _make_staff(client, admin, "tn4@bera.vn", CASHIER)

    r = client.get(
        f"{_DASHBOARD}/export", headers=_auth(admin), params={"target_type": "user_role"}
    )
    rows = list(csv.reader(io.StringIO(r.text)))
    body = rows[1:]
    assert body  # at least one role grant
    tt = CSV_HEADER.index("target_type")
    assert {row[tt] for row in body} == {"user_role"}


def test_a_cashier_cannot_export(client: TestClient) -> None:
    admin = _login(client)
    _make_staff(client, admin, "tn5@bera.vn", CASHIER)
    staff = _login(client, "tn5@bera.vn", STAFF_PASSWORD)
    assert client.get(f"{_DASHBOARD}/export", headers=_auth(staff)).status_code == 403


def test_export_with_unknown_actor_is_header_only(client: TestClient) -> None:
    admin = _login(client)
    r = client.get(
        f"{_DASHBOARD}/export", headers=_auth(admin), params={"actor_user_id": str(uuid4())}
    )
    rows = list(csv.reader(io.StringIO(r.text)))
    assert tuple(rows[0]) == CSV_HEADER
    assert len(rows) == 1  # header only, no matching entries


# --- read-only over HTTP ----------------------------------------------------


def test_dashboard_is_read_only(client: TestClient) -> None:
    admin = _login(client)
    for verb in (client.post, client.put, client.patch, client.delete):
        assert verb(_DASHBOARD, headers=_auth(admin)).status_code == 405
