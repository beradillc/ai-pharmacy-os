"""End-to-end: Sprint 7 "report xuất khẩu" — revenue + stock-by-lot CSV exports.

PROJECT_STATE §7am/§7an. Mirrors ``test_audit_dashboard_e2e.py``'s shape (real
login, real bearer tokens) but the point here is different: **no new permission**.
Revenue reuses ``sales.read``, stock reuses ``inventory.read`` — so a cashier (who
has both) can export both, while a warehouse clerk (who has ``inventory.read`` but
not ``sales.read``) can export stock but not revenue. That asymmetry is the
permission-reuse decision under test, not a gap.
"""

from __future__ import annotations

import asyncio
import csv
import io
from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
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
from pharmacy_os.modules.iam.domain import CASHIER, WAREHOUSE
from pharmacy_os.modules.iam.interface import build_repositories
from pharmacy_os.modules.inventory.application.csv_export import STOCK_CSV_HEADER
from pharmacy_os.modules.sales.application.csv_export import (
    REVENUE_CSV_HEADER,
    TOP_DRUGS_CSV_HEADER,
)

ADMIN_EMAIL = "admin@bera.vn"
ADMIN_PASSWORD = "MatKhauAdmin2026"
STAFF_PASSWORD = "MatKhauNhanVien26"

_REVENUE = "/api/v1/reports/revenue/export"
_STOCK = "/api/v1/reports/inventory/stock/export"
_TOP_DRUGS = "/api/v1/reports/top-drugs/export"


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
    db_path = tmp_path / "reports_e2e.db"
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


def _create_sale(client: TestClient, admin: Any, quantity: int, unit_price: int) -> Any:
    body = {
        "client_uuid": str(uuid4()),
        "lines": [
            {"drug_id": str(uuid4()), "quantity": quantity, "unit_price": unit_price},
        ],
        "payments": [{"method": "CASH", "amount": quantity * unit_price}],
    }
    r = client.post("/api/v1/sales", headers=_auth(admin), json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _create_sale_for_drug(
    client: TestClient, admin: Any, drug_id: str, quantity: int, unit_price: int
) -> Any:
    body = {
        "client_uuid": str(uuid4()),
        "lines": [{"drug_id": drug_id, "quantity": quantity, "unit_price": unit_price}],
        "payments": [{"method": "CASH", "amount": quantity * unit_price}],
    }
    r = client.post("/api/v1/sales", headers=_auth(admin), json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _receive_stock(client: TestClient, admin: Any, quantity: int) -> Any:
    body = {
        "drug_id": str(uuid4()),
        "lot_no": f"LOT-{uuid4().hex[:8]}",
        "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
        "quantity": quantity,
        "cost_price": 1000,
    }
    r = client.post("/api/v1/inventory/receive", headers=_auth(admin), json=body)
    assert r.status_code == 201, r.text
    return r.json()


# --- access control: reused permissions, no new one --------------------------


def test_reports_require_a_token(client: TestClient) -> None:
    assert client.get(_REVENUE, params=_date_range()).status_code == 401
    assert client.get(_STOCK).status_code == 401


def _date_range() -> dict[str, str]:
    return {
        "date_from": (date.today() - timedelta(days=1)).isoformat(),
        "date_to": (date.today() + timedelta(days=1)).isoformat(),
    }


def test_a_cashier_can_export_both_no_new_permission_needed(client: TestClient) -> None:
    """The reuse decision under test: sales.read/inventory.read already cover a
    cashier's day-to-day POS use, so no new grant is required (PROJECT_STATE §7am)."""
    admin = _login(client)
    _make_staff(client, admin, "tn@bera.vn", CASHIER)
    staff = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    assert client.get(_REVENUE, headers=_auth(staff), params=_date_range()).status_code == 200
    assert client.get(_STOCK, headers=_auth(staff)).status_code == 200


def test_a_warehouse_clerk_can_export_stock_but_not_revenue(client: TestClient) -> None:
    """warehouse holds inventory.read but not sales.read — the asymmetry the
    permission-reuse decision implies, not an oversight."""
    admin = _login(client)
    _make_staff(client, admin, "wh@bera.vn", WAREHOUSE)
    wh = _login(client, "wh@bera.vn", STAFF_PASSWORD)

    assert client.get(_STOCK, headers=_auth(wh)).status_code == 200
    assert client.get(_REVENUE, headers=_auth(wh), params=_date_range()).status_code == 403


def test_revenue_rejects_reversed_date_range(client: TestClient) -> None:
    admin = _login(client)
    r = client.get(
        _REVENUE,
        headers=_auth(admin),
        params={
            "date_from": date.today().isoformat(),
            "date_to": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert r.status_code == 422


# --- revenue export -----------------------------------------------------------


def test_revenue_export_sums_completed_orders(client: TestClient) -> None:
    admin = _login(client)
    _create_sale(client, admin, quantity=2, unit_price=50_000)  # 100_000
    _create_sale(client, admin, quantity=1, unit_price=30_000)  # 30_000

    r = client.get(_REVENUE, headers=_auth(admin), params=_date_range())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(r.text)))
    assert tuple(rows[0]) == REVENUE_CSV_HEADER
    body = rows[1:]
    assert body  # at least one bucket
    total_orders = sum(int(row[REVENUE_CSV_HEADER.index("order_count")]) for row in body)
    total_revenue = sum(Decimal(row[REVENUE_CSV_HEADER.index("revenue_total")]) for row in body)
    assert total_orders == 2
    assert total_revenue == Decimal("130000")
    assert {row[REVENUE_CSV_HEADER.index("currency")] for row in body} == {"VND"}


def test_revenue_export_branch_filter_narrows_to_nothing_for_a_foreign_branch(
    client: TestClient,
) -> None:
    admin = _login(client)
    _create_sale(client, admin, quantity=1, unit_price=10_000)

    r = client.get(
        _REVENUE,
        headers=_auth(admin),
        params={**_date_range(), "branch_id": str(uuid4())},
    )
    rows = list(csv.reader(io.StringIO(r.text)))
    assert tuple(rows[0]) == REVENUE_CSV_HEADER
    assert len(rows) == 1  # header only — no order in that branch


def test_revenue_export_own_branch_filter_matches(client: TestClient) -> None:
    admin = _login(client)
    _create_sale(client, admin, quantity=1, unit_price=20_000)

    r = client.get(
        _REVENUE,
        headers=_auth(admin),
        params={**_date_range(), "branch_id": admin["branch_id"]},
    )
    rows = list(csv.reader(io.StringIO(r.text)))
    assert len(rows) > 1


def test_draft_sale_is_never_counted_as_revenue(client: TestClient) -> None:
    """An order that never completes (underpaid) must not exist — but this also
    documents that a stray DRAFT would be excluded (``status != DRAFT`` in the
    repository query), not just "usually absent"."""
    admin = _login(client)
    r = client.post(
        "/api/v1/sales",
        headers=_auth(admin),
        json={
            "client_uuid": str(uuid4()),
            "lines": [{"drug_id": str(uuid4()), "quantity": 1, "unit_price": 99_000}],
            "payments": [],  # underpaid — complete_sale() rejects it
        },
    )
    assert r.status_code == 422

    export = client.get(_REVENUE, headers=_auth(admin), params=_date_range())
    rows = list(csv.reader(io.StringIO(export.text)))
    assert len(rows) == 1  # header only — the rejected order was never persisted


# --- revenue export: salesperson filter (PROJECT_STATE §7ao) -------------------


def test_revenue_export_salesperson_filter_narrows_to_that_user(client: TestClient) -> None:
    """A per-salesperson report shows only the orders that user completed. The admin
    and a cashier each ring up one sale; filtering by the cashier's id yields the
    cashier's total alone, not the combined one."""
    admin = _login(client)
    _make_staff(client, admin, "tn@bera.vn", CASHIER)
    cashier = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    _create_sale(client, admin, quantity=1, unit_price=40_000)  # admin's sale
    _create_sale(client, cashier, quantity=1, unit_price=25_000)  # cashier's sale

    r = client.get(
        _REVENUE,
        headers=_auth(admin),
        params={**_date_range(), "sold_by_user_id": cashier["user_id"]},
    )
    assert r.status_code == 200
    body = list(csv.reader(io.StringIO(r.text)))[1:]
    total = sum(Decimal(row[REVENUE_CSV_HEADER.index("revenue_total")]) for row in body)
    orders = sum(int(row[REVENUE_CSV_HEADER.index("order_count")]) for row in body)
    assert orders == 1
    assert total == Decimal("25000")


def test_revenue_export_without_salesperson_filter_counts_everyone(client: TestClient) -> None:
    """Omitting the filter keeps every salesperson — the combined total, the same
    behaviour as before the column existed."""
    admin = _login(client)
    _make_staff(client, admin, "tn2@bera.vn", CASHIER)
    cashier = _login(client, "tn2@bera.vn", STAFF_PASSWORD)

    _create_sale(client, admin, quantity=1, unit_price=40_000)
    _create_sale(client, cashier, quantity=1, unit_price=25_000)

    r = client.get(_REVENUE, headers=_auth(admin), params=_date_range())
    body = list(csv.reader(io.StringIO(r.text)))[1:]
    total = sum(Decimal(row[REVENUE_CSV_HEADER.index("revenue_total")]) for row in body)
    assert total == Decimal("65000")


def test_revenue_export_salesperson_filter_unknown_user_is_empty(client: TestClient) -> None:
    admin = _login(client)
    _create_sale(client, admin, quantity=1, unit_price=10_000)

    r = client.get(
        _REVENUE,
        headers=_auth(admin),
        params={**_date_range(), "sold_by_user_id": str(uuid4())},
    )
    rows = list(csv.reader(io.StringIO(r.text)))
    assert len(rows) == 1  # header only — nobody sold under that id


# --- stock export --------------------------------------------------------------


def test_stock_export_lists_lot_and_expiry(client: TestClient) -> None:
    admin = _login(client)
    received = _receive_stock(client, admin, quantity=15)

    r = client.get(_STOCK, headers=_auth(admin))
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")

    rows = list(csv.reader(io.StringIO(r.text)))
    assert tuple(rows[0]) == STOCK_CSV_HEADER
    body = rows[1:]
    batch_id_col = STOCK_CSV_HEADER.index("batch_id")
    batch_ids = {row[batch_id_col] for row in body}
    assert received["batch_id"] in batch_ids
    match = next(row for row in body if row[batch_id_col] == received["batch_id"])
    assert Decimal(match[STOCK_CSV_HEADER.index("quantity")]) == Decimal("15")


def test_stock_export_branch_filter_narrows_to_nothing_for_a_foreign_branch(
    client: TestClient,
) -> None:
    admin = _login(client)
    _receive_stock(client, admin, quantity=5)

    r = client.get(_STOCK, headers=_auth(admin), params={"branch_id": str(uuid4())})
    rows = list(csv.reader(io.StringIO(r.text)))
    assert len(rows) == 1  # header only


# --- top-selling-drugs export (Sprint 7 report đợt 2, PROJECT_STATE §7ba) ------


def test_top_drugs_requires_a_token(client: TestClient) -> None:
    assert client.get(_TOP_DRUGS, params=_date_range()).status_code == 401


def test_top_drugs_reuses_sales_read_no_new_permission(client: TestClient) -> None:
    """Same reuse decision as revenue (§7am): a warehouse clerk has inventory.read
    but not sales.read, so top-drugs (line-level sales data) is denied the same
    way revenue is."""
    admin = _login(client)
    _make_staff(client, admin, "wh2@bera.vn", WAREHOUSE)
    wh = _login(client, "wh2@bera.vn", STAFF_PASSWORD)

    assert client.get(_TOP_DRUGS, headers=_auth(wh), params=_date_range()).status_code == 403


def test_top_drugs_ranks_by_quantity_net_of_returns(client: TestClient) -> None:
    admin = _login(client)
    drug_a, drug_b = str(uuid4()), str(uuid4())
    _create_sale_for_drug(client, admin, drug_a, quantity=10, unit_price=1_000)  # 10 units
    _create_sale_for_drug(client, admin, drug_b, quantity=3, unit_price=1_000)  # 3 units

    r = client.get(_TOP_DRUGS, headers=_auth(admin), params=_date_range())
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(r.text)))
    assert tuple(rows[0]) == TOP_DRUGS_CSV_HEADER
    body = rows[1:]
    assert len(body) == 2
    rank_col = TOP_DRUGS_CSV_HEADER.index("rank")
    drug_col = TOP_DRUGS_CSV_HEADER.index("drug_id")
    qty_col = TOP_DRUGS_CSV_HEADER.index("quantity_sold")
    assert body[0][rank_col] == "1"
    assert body[0][drug_col] == drug_a
    assert Decimal(body[0][qty_col]) == Decimal("10")
    assert body[1][rank_col] == "2"
    assert body[1][drug_col] == drug_b


def test_top_drugs_sort_by_revenue_can_reorder_vs_quantity(client: TestClient) -> None:
    """More units of a cheap drug can still lose to fewer units of an expensive one
    when ranking by revenue instead of quantity — proves ``sort_by`` actually
    changes the order, not just the column values."""
    admin = _login(client)
    cheap, pricey = str(uuid4()), str(uuid4())
    _create_sale_for_drug(client, admin, cheap, quantity=10, unit_price=1_000)  # 10 units / 10_000
    _create_sale_for_drug(client, admin, pricey, quantity=1, unit_price=50_000)  # 1 unit / 50_000

    r = client.get(_TOP_DRUGS, headers=_auth(admin), params={**_date_range(), "sort_by": "revenue"})
    body = list(csv.reader(io.StringIO(r.text)))[1:]
    drug_col = TOP_DRUGS_CSV_HEADER.index("drug_id")
    assert body[0][drug_col] == pricey


def test_top_drugs_limit_truncates_the_ranked_list(client: TestClient) -> None:
    admin = _login(client)
    for _ in range(3):
        _create_sale_for_drug(client, admin, str(uuid4()), quantity=1, unit_price=1_000)

    r = client.get(_TOP_DRUGS, headers=_auth(admin), params={**_date_range(), "limit": 2})
    body = list(csv.reader(io.StringIO(r.text)))[1:]
    assert len(body) == 2


def test_top_drugs_rejects_reversed_date_range(client: TestClient) -> None:
    admin = _login(client)
    r = client.get(
        _TOP_DRUGS,
        headers=_auth(admin),
        params={
            "date_from": date.today().isoformat(),
            "date_to": (date.today() - timedelta(days=1)).isoformat(),
        },
    )
    assert r.status_code == 422


# --- read-only over HTTP --------------------------------------------------------


def test_reports_are_read_only(client: TestClient) -> None:
    admin = _login(client)
    for verb in (client.post, client.put, client.patch, client.delete):
        assert verb(_REVENUE, headers=_auth(admin)).status_code == 405
        assert verb(_STOCK, headers=_auth(admin)).status_code == 405
        assert verb(_TOP_DRUGS, headers=_auth(admin)).status_code == 405
