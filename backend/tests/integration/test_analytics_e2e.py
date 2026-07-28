"""End-to-end: analytics reorder flow + dashboard over the real wired app.

Exercises the composition-root adapters (sales/inventory/procurement → analytics)
that the service-level ``test_analytics_flow`` fakes: a real sale builds velocity and
draws stock down, a real placed PO gives the drug a supplier, then a reorder run
suggests, materialises a DRAFT PO, and the dashboard reports it. Also checks the new
``analytics.*`` permission boundary (a cashier is refused).
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import date, timedelta
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
    db_path = tmp_path / "analytics_e2e.db"
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


def _make_staff(client: TestClient, admin: Any, email: str, role_code: str) -> None:
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    role = next(r for r in roles if r["code"] == role_code)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": email, "password": STAFF_PASSWORD, "full_name": "Nhân Viên"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": role["id"], "branch_id": admin["branch_id"]},
    )


def _receive(client: TestClient, admin: Any, drug_id: str, qty: int) -> None:
    r = client.post(
        "/api/v1/inventory/receive",
        headers=_auth(admin),
        json={
            "drug_id": drug_id,
            "lot_no": f"LOT-{uuid4().hex[:8]}",
            "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
            "quantity": qty,
            "cost_price": 1000,
        },
    )
    assert r.status_code == 201, r.text


def _sell(client: TestClient, admin: Any, drug_id: str, qty: int, price: int) -> None:
    r = client.post(
        "/api/v1/sales",
        headers=_auth(admin),
        json={
            "client_uuid": str(uuid4()),
            "lines": [{"drug_id": drug_id, "quantity": qty, "unit_price": price}],
            "payments": [{"method": "CASH", "amount": qty * price}],
        },
    )
    assert r.status_code == 201, r.text


def _supplier_for_drug(client: TestClient, admin: Any, drug_id: str) -> str:
    supplier_id = client.post(
        "/api/v1/suppliers", headers=_auth(admin), json={"name": "NCC Chính"}
    ).json()["id"]
    po = client.post(
        "/api/v1/purchase-orders",
        headers=_auth(admin),
        json={
            "supplier_id": supplier_id,
            "items": [{"drug_id": drug_id, "quantity_ordered": 10, "unit_price": 900}],
        },
    ).json()
    # Place it so it counts as a real supplier relationship (past DRAFT).
    r = client.post(f"/api/v1/purchase-orders/{po['id']}/place", headers=_auth(admin))
    assert r.status_code == 200, r.text
    return supplier_id


_RUN = "/api/v1/analytics/reorder/run"
_SUGGESTIONS = "/api/v1/analytics/reorder/suggestions"
_DASHBOARD = "/api/v1/analytics/dashboard"


def test_reorder_run_suggests_low_stock_drug_and_materializes(client: TestClient) -> None:
    admin = _login(client)
    drug = str(uuid4())
    supplier_id = _supplier_for_drug(client, admin, drug)
    _receive(client, admin, drug, qty=100)
    _sell(client, admin, drug, qty=90, price=1000)  # velocity 1/day, on-hand → 10 (== point)

    run = client.post(_RUN, headers=_auth(admin))
    assert run.status_code == 200, run.text
    assert run.json()["suggested"] == 1

    suggestions = client.get(
        _SUGGESTIONS, headers=_auth(admin), params={"status": "PENDING"}
    ).json()
    assert len(suggestions) == 1
    s = suggestions[0]
    assert s["drug_id"] == drug
    assert s["supplier_id"] == supplier_id
    assert s["can_materialize"] is True

    mat = client.post(f"{_SUGGESTIONS}/{s['id']}/materialize", headers=_auth(admin))
    assert mat.status_code == 200, mat.text
    po_id = mat.json()["po_id"]

    # The materialised PO is a real DRAFT purchase order in procurement.
    po = client.get(f"/api/v1/purchase-orders/{po_id}", headers=_auth(admin)).json()
    assert po["status"] == "DRAFT"
    assert po["items"][0]["drug_id"] == drug


def test_dashboard_reports_tiles(client: TestClient) -> None:
    admin = _login(client)
    drug = str(uuid4())
    _supplier_for_drug(client, admin, drug)
    _receive(client, admin, drug, qty=100)
    _sell(client, admin, drug, qty=90, price=1000)
    client.post(_RUN, headers=_auth(admin))

    today = date.today()
    dash = client.get(
        _DASHBOARD,
        headers=_auth(admin),
        params={
            "date_from": (today - timedelta(days=30)).isoformat(),
            "date_to": today.isoformat(),
        },
    )
    assert dash.status_code == 200, dash.text
    body = dash.json()
    from decimal import Decimal

    assert Decimal(body["revenue_total"]) == Decimal("90000")
    assert body["top_drugs"][0]["drug_id"] == drug
    assert body["low_stock_count"] >= 1


def test_analytics_requires_token(client: TestClient) -> None:
    assert client.post(_RUN).status_code == 401
    assert client.get(_SUGGESTIONS).status_code == 401


def test_cashier_is_refused_analytics(client: TestClient) -> None:
    admin = _login(client)
    _make_staff(client, admin, "tn@bera.vn", CASHIER)
    cashier = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    assert client.post(_RUN, headers=_auth(cashier)).status_code == 403
    assert client.get(_SUGGESTIONS, headers=_auth(cashier)).status_code == 403
    assert (
        client.get(
            _DASHBOARD,
            headers=_auth(cashier),
            params={"date_from": date.today().isoformat(), "date_to": date.today().isoformat()},
        ).status_code
        == 403
    )


# --- G-1 (docs/19): hai màn Sprint 9 phải in TÊN, không in UUID ----------------


def _create_drug(client: TestClient, admin: Any, name: str) -> str:
    r = client.post(
        "/api/v1/drugs",
        headers=_auth(admin),
        json={"name": name, "rx_class": "OTC", "base_unit": "viên"},
    )
    assert r.status_code == 201, r.text
    drug_id: str = r.json()["id"]
    return drug_id


def test_suggestion_and_dashboard_expose_drug_name_over_http(client: TestClient) -> None:
    """Reads the wired app, not the service: proves the catalog adapter is connected."""
    admin = _login(client)
    drug = _create_drug(client, admin, "Amoxicillin 500mg")
    _supplier_for_drug(client, admin, drug)
    _receive(client, admin, drug, qty=100)
    _sell(client, admin, drug, qty=90, price=1000)
    client.post(_RUN, headers=_auth(admin))

    suggestions = client.get(_SUGGESTIONS, headers=_auth(admin), params={"status": "PENDING"})
    assert suggestions.status_code == 200, suggestions.text
    assert suggestions.json()[0]["drug_name"] == "Amoxicillin 500mg"

    today = date.today()
    dash = client.get(
        _DASHBOARD,
        headers=_auth(admin),
        params={
            "date_from": (today - timedelta(days=30)).isoformat(),
            "date_to": today.isoformat(),
        },
    )
    assert dash.status_code == 200, dash.text
    assert dash.json()["top_drugs"][0]["drug_name"] == "Amoxicillin 500mg"


def test_drug_with_no_catalog_row_returns_null_name_not_an_error(client: TestClient) -> None:
    """Stock can exist for an id catalog never knew (the other tests in this file rely
    on exactly that). The screen must degrade to a null label, not to a 500."""
    admin = _login(client)
    drug = str(uuid4())
    _supplier_for_drug(client, admin, drug)
    _receive(client, admin, drug, qty=100)
    _sell(client, admin, drug, qty=90, price=1000)
    client.post(_RUN, headers=_auth(admin))

    suggestions = client.get(_SUGGESTIONS, headers=_auth(admin), params={"status": "PENDING"})
    assert suggestions.status_code == 200, suggestions.text
    assert suggestions.json()[0]["drug_name"] is None
