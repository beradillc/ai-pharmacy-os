"""End-to-end HTTP test for the procurement module (routing, DI, dev context, DB)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
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
    db_path = tmp_path / "procurement_api.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _expiry() -> str:
    return (date.today() + timedelta(days=365)).isoformat()


def _create_supplier(client: TestClient, name: str = "Dược Trung Ương") -> dict[str, object]:
    resp = client.post("/api/v1/suppliers", json={"name": name})
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_ordered_po(client: TestClient, *, quantity: str = "100") -> dict[str, object]:
    """Create a supplier + PO with one line, place the order (status ORDERED)."""
    supplier = _create_supplier(client)
    drug_id = str(uuid4())
    created = client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier["id"],
            "items": [{"drug_id": drug_id, "quantity_ordered": quantity, "unit_price": "5000"}],
        },
    )
    assert created.status_code == 201, created.text
    po = created.json()
    ordered = client.post(f"/api/v1/purchase-orders/{po['id']}/place")
    assert ordered.status_code == 200, ordered.text
    return ordered.json()


def test_create_and_get_supplier(client: TestClient) -> None:
    created = _create_supplier(client)
    assert created["is_active"] is True

    fetched = client.get(f"/api/v1/suppliers/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Dược Trung Ương"


def test_list_suppliers_ordered_by_name(client: TestClient) -> None:
    _create_supplier(client, name="Bình")
    _create_supplier(client, name="An")
    resp = client.get("/api/v1/suppliers")
    assert resp.status_code == 200
    assert [s["name"] for s in resp.json()] == ["An", "Bình"]


def test_get_unknown_supplier_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/suppliers/{uuid4()}")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_invalid_supplier_name_rejected_by_schema(client: TestClient) -> None:
    resp = client.post("/api/v1/suppliers", json={"name": ""})
    assert resp.status_code == 422


def test_create_purchase_order_with_items_then_read_back(client: TestClient) -> None:
    supplier = _create_supplier(client)
    drug_id = str(uuid4())
    created = client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier["id"],
            "items": [{"drug_id": drug_id, "quantity_ordered": "50", "unit_price": "2000"}],
        },
    )
    assert created.status_code == 201, created.text
    po = created.json()
    assert po["status"] == "DRAFT"
    assert po["items"][0]["drug_id"] == drug_id

    got = client.get(f"/api/v1/purchase-orders/{po['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == po["id"]


def test_add_item_place_cancel_and_state_guards(client: TestClient) -> None:
    supplier = _create_supplier(client)
    created = client.post(
        "/api/v1/purchase-orders", json={"supplier_id": supplier["id"], "items": []}
    ).json()

    with_item = client.post(
        f"/api/v1/purchase-orders/{created['id']}/items",
        json={"drug_id": str(uuid4()), "quantity_ordered": "10", "unit_price": "1000"},
    )
    assert with_item.status_code == 201, with_item.text
    assert len(with_item.json()["items"]) == 1

    placed = client.post(f"/api/v1/purchase-orders/{created['id']}/place")
    assert placed.status_code == 200, placed.text
    assert placed.json()["status"] == "ORDERED"

    blocked_item = client.post(
        f"/api/v1/purchase-orders/{created['id']}/items",
        json={"drug_id": str(uuid4()), "quantity_ordered": "1", "unit_price": "1"},
    )
    assert blocked_item.status_code == 422, blocked_item.text

    blocked_cancel = client.post(f"/api/v1/purchase-orders/{created['id']}/cancel")
    assert blocked_cancel.status_code == 422, blocked_cancel.text


def test_cancel_from_draft(client: TestClient) -> None:
    supplier = _create_supplier(client)
    created = client.post(
        "/api/v1/purchase-orders", json={"supplier_id": supplier["id"], "items": []}
    ).json()
    cancelled = client.post(f"/api/v1/purchase-orders/{created['id']}/cancel")
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "CANCELLED"


def test_place_order_empty_rejected(client: TestClient) -> None:
    supplier = _create_supplier(client)
    created = client.post(
        "/api/v1/purchase-orders", json={"supplier_id": supplier["id"], "items": []}
    ).json()
    resp = client.post(f"/api/v1/purchase-orders/{created['id']}/place")
    assert resp.status_code == 422
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_full_receipt_flow_reaches_received_then_closed(client: TestClient) -> None:
    po = _create_ordered_po(client, quantity="100")
    drug_id = po["items"][0]["drug_id"]
    po_item_id = po["items"][0]["id"]

    created_grn = client.post(
        "/api/v1/goods-receipts",
        json={
            "po_id": po["id"],
            "items": [
                {
                    "po_item_id": po_item_id,
                    "drug_id": drug_id,
                    "quantity_received": "100",
                    "lot_no": "LOT001",
                    "expiry_date": _expiry(),
                    "unit_cost": "4800",
                }
            ],
        },
    )
    assert created_grn.status_code == 201, created_grn.text
    grn = created_grn.json()
    assert grn["status"] == "DRAFT"

    confirmed = client.post(f"/api/v1/goods-receipts/{grn['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"

    updated_po = client.get(f"/api/v1/purchase-orders/{po['id']}")
    assert updated_po.json()["status"] == "RECEIVED"

    closed = client.post(f"/api/v1/purchase-orders/{po['id']}/close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "CLOSED"


def test_partial_receipt_leaves_po_partially_received(client: TestClient) -> None:
    po = _create_ordered_po(client, quantity="100")
    drug_id = po["items"][0]["drug_id"]
    po_item_id = po["items"][0]["id"]

    grn = client.post(
        "/api/v1/goods-receipts",
        json={
            "po_id": po["id"],
            "items": [
                {
                    "po_item_id": po_item_id,
                    "drug_id": drug_id,
                    "quantity_received": "40",
                    "lot_no": "LOT002",
                    "expiry_date": _expiry(),
                    "unit_cost": "4800",
                }
            ],
        },
    ).json()
    client.post(f"/api/v1/goods-receipts/{grn['id']}/confirm")

    updated_po = client.get(f"/api/v1/purchase-orders/{po['id']}").json()
    assert updated_po["status"] == "PARTIALLY_RECEIVED"
    assert Decimal(updated_po["items"][0]["quantity_received"]) == Decimal("40")


def test_over_receipt_rejected(client: TestClient) -> None:
    po = _create_ordered_po(client, quantity="10")
    drug_id = po["items"][0]["drug_id"]
    po_item_id = po["items"][0]["id"]

    grn = client.post(
        "/api/v1/goods-receipts",
        json={
            "po_id": po["id"],
            "items": [
                {
                    "po_item_id": po_item_id,
                    "drug_id": drug_id,
                    "quantity_received": "999",
                    "lot_no": "LOT003",
                    "expiry_date": _expiry(),
                    "unit_cost": "100",
                }
            ],
        },
    ).json()
    resp = client.post(f"/api/v1/goods-receipts/{grn['id']}/confirm")
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_unknown_po_item_id_rejected_with_422_not_500(client: TestClient) -> None:
    po = _create_ordered_po(client, quantity="10")
    resp = client.post(
        "/api/v1/goods-receipts",
        json={
            "po_id": po["id"],
            "items": [
                {
                    "po_item_id": str(uuid4()),
                    "drug_id": str(uuid4()),
                    "quantity_received": "1",
                    "lot_no": "LOT004",
                    "expiry_date": _expiry(),
                    "unit_cost": "1",
                }
            ],
        },
    )
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_create_goods_receipt_unknown_po_404(client: TestClient) -> None:
    resp = client.post("/api/v1/goods-receipts", json={"po_id": str(uuid4()), "items": []})
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_get_unknown_goods_receipt_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/goods-receipts/{uuid4()}")
    assert resp.status_code == 404
