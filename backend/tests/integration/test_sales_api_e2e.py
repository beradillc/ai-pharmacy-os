"""End-to-end HTTP test for the sales module (routing, DI, dev context, DB)."""

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
    db_path = tmp_path / "sales_api.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _payload(client_uuid: str, *, rx: bool = False, rx_ref: str | None = None) -> dict[str, object]:
    return {
        "client_uuid": client_uuid,
        "lines": [
            {
                "drug_id": str(uuid4()),
                "quantity": "2",
                "unit_price": "10000",
                "requires_prescription": rx,
            }
        ],
        "payments": [{"method": "CASH", "amount": "20000"}],
        "prescription_ref": rx_ref,
    }


def test_create_sale_then_read_back(client: TestClient) -> None:
    resp = client.post("/api/v1/sales", json=_payload("pos-1"))
    assert resp.status_code == 201, resp.text
    sale = resp.json()
    assert sale["status"] == "COMPLETED"
    assert sale["subtotal"] == "20000.00"

    got = client.get(f"/api/v1/sales/{sale['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == sale["id"]


def test_sync_is_idempotent(client: TestClient) -> None:
    first = client.post("/api/v1/sync/sales", json=_payload("offline-1"))
    assert first.status_code == 200, first.text
    second = client.post("/api/v1/sync/sales", json=_payload("offline-1"))
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]  # no duplicate order


def test_etc_without_prescription_rejected(client: TestClient) -> None:
    resp = client.post("/api/v1/sales", json=_payload("etc-1", rx=True))
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_etc_with_prescription_allowed(client: TestClient) -> None:
    resp = client.post("/api/v1/sales", json=_payload("etc-2", rx=True, rx_ref=str(uuid4())))
    assert resp.status_code == 201, resp.text


def test_empty_lines_rejected_by_schema(client: TestClient) -> None:
    resp = client.post("/api/v1/sales", json={"client_uuid": "x", "lines": [], "payments": []})
    assert resp.status_code == 422
