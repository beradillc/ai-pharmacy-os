"""End-to-end: a completed sale drives an inventory dispense (cross-module)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.config import AppSettings, DatabaseSettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "sales_inv.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _receive(client: TestClient, drug_id: str, qty: str) -> None:
    r = client.post(
        "/api/v1/inventory/receive",
        json={
            "drug_id": drug_id,
            "lot_no": "L1",
            "expiry_date": "2027-01-01",
            "quantity": qty,
            "cost_price": "1000",
        },
    )
    assert r.status_code == 201, r.text


def _on_hand(client: TestClient, drug_id: str) -> str:
    r = client.get("/api/v1/inventory/on-hand", params={"drug_id": drug_id})
    assert r.status_code == 200
    return str(r.json()["on_hand"])


def _sale_body(client_uuid: str, drug_id: str, qty: str) -> dict[str, object]:
    return {
        "client_uuid": client_uuid,
        "lines": [{"drug_id": drug_id, "quantity": qty, "unit_price": "10000"}],
        "payments": [{"method": "CASH", "amount": "999999"}],
    }


def test_sale_decrements_stock_via_event(client: TestClient) -> None:
    drug = str(uuid4())
    _receive(client, drug, "20")

    resp = client.post("/api/v1/sales", json=_sale_body("pos-1", drug, "12"))
    assert resp.status_code == 201, resp.text
    assert _on_hand(client, drug) == "8.000"  # dispensed by the SaleCompleted reaction


def test_resync_does_not_double_dispense(client: TestClient) -> None:
    drug = str(uuid4())
    _receive(client, drug, "20")

    client.post("/api/v1/sync/sales", json=_sale_body("offline-1", drug, "12"))
    client.post("/api/v1/sync/sales", json=_sale_body("offline-1", drug, "12"))  # retried
    assert _on_hand(client, drug) == "8.000"  # decremented exactly once


def test_oversell_does_not_go_negative(client: TestClient) -> None:
    drug = str(uuid4())
    _receive(client, drug, "5")

    resp = client.post("/api/v1/sales", json=_sale_body("pos-2", drug, "10"))
    assert resp.status_code == 201, resp.text  # sale not blocked
    assert _on_hand(client, drug) == "0.000"  # available part dispensed, never negative
