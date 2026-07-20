"""End-to-end HTTP test: full stack (routing, DI, dev context, repos, DB)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.config import AppSettings, DatabaseSettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "api.db"
    # Create the schema up-front via a sync engine on the same file.
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def test_catalog_and_inventory_flow(client: TestClient) -> None:
    # 1) Create a drug.
    resp = client.post(
        "/api/v1/drugs",
        json={
            "name": "Amoxicillin 500mg",
            "rx_class": "ETC",
            "base_unit": "viên",
            "units": [{"unit_name": "vỉ", "factor": "10"}],
        },
    )
    assert resp.status_code == 201, resp.text
    drug = resp.json()
    assert drug["prescription_required"] is True
    drug_id = drug["id"]

    # 2) Receive two batches (near + far expiry).
    for lot, expiry in (("FAR", "2027-01-01"), ("NEAR", "2026-08-01")):
        r = client.post(
            "/api/v1/inventory/receive",
            json={
                "drug_id": drug_id,
                "lot_no": lot,
                "expiry_date": expiry,
                "quantity": "10",
                "cost_price": "1000",
            },
        )
        assert r.status_code == 201, r.text

    # 3) On-hand reflects both receipts.
    r = client.get("/api/v1/inventory/on-hand", params={"drug_id": drug_id})
    assert r.json()["on_hand"] == "20.000"

    # 4) FEFO dispense pulls from the nearer-expiry batch first.
    r = client.post("/api/v1/inventory/dispense", json={"drug_id": drug_id, "quantity": "12"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["on_hand"] == "8.000"
    assert body["allocations"][0]["quantity"] == "10.000"

    # 5) Over-dispensing is rejected.
    r = client.post("/api/v1/inventory/dispense", json={"drug_id": drug_id, "quantity": "999"})
    assert r.status_code == 409


def test_unknown_drug_returns_404(client: TestClient) -> None:
    resp = client.get("/api/v1/drugs/00000000-0000-0000-0000-0000000000ff")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
