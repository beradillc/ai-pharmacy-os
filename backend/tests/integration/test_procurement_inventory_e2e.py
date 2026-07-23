"""End-to-end: confirming a goods-receipt note drives an inventory stock-in (cross-module).

Exercises the real wiring in ``build_api_router`` (``wire_goods_receipt_stock_in``):
procurement HTTP flow -> ``GoodsReceived`` -> inventory batch created.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "proc_inv.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
        security=SecuritySettings(allow_dev_auth=True),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _expiry() -> str:
    return (date.today() + timedelta(days=365)).isoformat()


def _on_hand(client: TestClient, drug_id: str) -> Decimal:
    r = client.get("/api/v1/inventory/on-hand", params={"drug_id": drug_id})
    assert r.status_code == 200, r.text
    return Decimal(str(r.json()["on_hand"]))


def _ordered_po(client: TestClient, drug_id: str, qty: str) -> dict[str, object]:
    supplier = client.post("/api/v1/suppliers", json={"name": "NCC"}).json()
    created = client.post(
        "/api/v1/purchase-orders",
        json={
            "supplier_id": supplier["id"],
            "items": [{"drug_id": drug_id, "quantity_ordered": qty, "unit_price": "5000"}],
        },
    )
    assert created.status_code == 201, created.text
    po = created.json()
    placed = client.post(f"/api/v1/purchase-orders/{po['id']}/place")
    assert placed.status_code == 200, placed.text
    return placed.json()


def test_confirming_grn_creates_inventory_stock(client: TestClient) -> None:
    drug = str(uuid4())
    po = _ordered_po(client, drug, "100")
    assert _on_hand(client, drug) == Decimal("0")  # nothing received yet

    grn = client.post(
        "/api/v1/goods-receipts",
        json={
            "po_id": po["id"],
            "items": [
                {
                    "po_item_id": po["items"][0]["id"],
                    "drug_id": drug,
                    "quantity_received": "100",
                    "lot_no": "LOT-E2E-1",
                    "expiry_date": _expiry(),
                    "unit_cost": "4800",
                }
            ],
        },
    ).json()

    confirmed = client.post(f"/api/v1/goods-receipts/{grn['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "CONFIRMED"

    # The GoodsReceived reaction created the inventory batch.
    assert _on_hand(client, drug) == Decimal("100")


def test_two_partial_receipts_accumulate_stock(client: TestClient) -> None:
    drug = str(uuid4())
    po = _ordered_po(client, drug, "100")
    po_item_id = po["items"][0]["id"]

    def receive(lot: str, qty: str) -> None:
        grn = client.post(
            "/api/v1/goods-receipts",
            json={
                "po_id": po["id"],
                "items": [
                    {
                        "po_item_id": po_item_id,
                        "drug_id": drug,
                        "quantity_received": qty,
                        "lot_no": lot,
                        "expiry_date": _expiry(),
                        "unit_cost": "4800",
                    }
                ],
            },
        ).json()
        assert client.post(f"/api/v1/goods-receipts/{grn['id']}/confirm").status_code == 200

    receive("LOT-A", "40")
    receive("LOT-B", "60")  # distinct lots -> two batches -> accumulate

    assert _on_hand(client, drug) == Decimal("100")
