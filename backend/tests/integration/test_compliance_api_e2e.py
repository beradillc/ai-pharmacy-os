"""End-to-end over HTTP: the compliance router mounted for the first time (§7n/§7p).

Confirms the wiring, not the domain rules (those are covered by unit tests in
``tests/unit`` for the ledger/config/sync services) — real token, real DI resolution,
real response shape.
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

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
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
    db_path = tmp_path / "compliance_e2e.db"
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
    with TestClient(create_app(settings)) as c:
        yield c


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD) -> Any:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(session: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def test_admin_records_and_reads_back_a_controlled_ledger_entry(client: TestClient) -> None:
    admin = _login(client)
    created = client.post(
        "/api/v1/compliance/controlled-ledger",
        headers=_auth(admin),
        json={
            "drug_id": str(uuid4()),
            "category": "HUONG_THAN",
            "direction": "NHAP",
            "quantity": "10",
            "lot_no": "L001",
            "expiry_date": "2027-01-01",
            "transaction_at": "2026-07-23T09:00:00Z",
            "source_or_destination": "Công ty Dược ABC",
            "document_no": "PN-001",
        },
    )
    assert created.status_code == 201, created.text
    entry_id = created.json()["id"]

    fetched = client.get(f"/api/v1/compliance/controlled-ledger/{entry_id}", headers=_auth(admin))
    assert fetched.status_code == 200
    assert fetched.json()["document_no"] == "PN-001"


def test_admin_sets_and_reads_tenant_config(client: TestClient) -> None:
    admin = _login(client)
    r = client.put(
        "/api/v1/compliance/tenant-config",
        headers=_auth(admin),
        json={"ma_co_so_ban_le": "ABC123"},
    )
    assert r.status_code == 200
    assert r.json()["ma_co_so_ban_le"] == "ABC123"

    fetched = client.get("/api/v1/compliance/tenant-config", headers=_auth(admin))
    assert fetched.status_code == 200
    assert fetched.json()["ma_co_so_ban_le"] == "ABC123"


def test_admin_pushes_and_reads_a_sync_log(client: TestClient) -> None:
    admin = _login(client)
    client_uuid = str(uuid4())
    pushed = client.post(
        "/api/v1/compliance/sync-logs",
        headers=_auth(admin),
        json={"payload_type": "sale", "client_uuid": client_uuid, "payload": "{}"},
    )
    assert pushed.status_code == 201, pushed.text
    log_id = pushed.json()["id"]
    assert pushed.json()["status"] == "ACK"  # mock gateway always ACKs

    fetched = client.get(f"/api/v1/compliance/sync-logs/{log_id}", headers=_auth(admin))
    assert fetched.status_code == 200
    assert fetched.json()["client_uuid"] == client_uuid


def test_cashier_cannot_write_the_controlled_ledger(client: TestClient) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    cashier_role = next(r for r in roles if r["code"] == CASHIER)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "tn@bera.vn", "password": STAFF_PASSWORD, "full_name": "Thu Ngân"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    cashier = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    r = client.post(
        "/api/v1/compliance/controlled-ledger",
        headers=_auth(cashier),
        json={
            "drug_id": str(uuid4()),
            "category": "HUONG_THAN",
            "direction": "NHAP",
            "quantity": "1",
            "lot_no": "L1",
            "expiry_date": "2027-01-01",
            "transaction_at": "2026-07-23T09:00:00Z",
            "source_or_destination": "X",
            "document_no": "D1",
        },
    )
    assert r.status_code == 403


def test_the_ledger_needs_a_token(client: TestClient) -> None:
    assert client.get(f"/api/v1/compliance/controlled-ledger/{uuid4()}").status_code == 401
