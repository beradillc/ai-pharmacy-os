"""End-to-end HTTP test: full stack (routing, DI, dev context, repos, DB)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from tests.conftest import urls_csdl_thu


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "api.db"
    _sync_url, _async_url = urls_csdl_thu(db_path)
    # Create the schema up-front via a sync engine on the same file.
    sync_engine = create_engine(_sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=_async_url),
        security=SecuritySettings(allow_dev_auth=True),
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
    assert Decimal(r.json()["on_hand"]) == Decimal("20.000")

    # 4) FEFO dispense pulls from the nearer-expiry batch first.
    r = client.post("/api/v1/inventory/dispense", json={"drug_id": drug_id, "quantity": "12"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert Decimal(body["on_hand"]) == Decimal("8.000")
    assert Decimal(body["allocations"][0]["quantity"]) == Decimal("10.000")

    # 5) Over-dispensing is rejected.
    r = client.post("/api/v1/inventory/dispense", json={"drug_id": drug_id, "quantity": "999"})
    assert r.status_code == 409


def test_unknown_drug_returns_404(client: TestClient) -> None:
    resp = client.get("/api/v1/drugs/00000000-0000-0000-0000-0000000000ff")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_active_ingredients_crud(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/active-ingredients", json={"name": "Amoxicillin", "name_en": "Amoxicillin"}
    )
    assert resp.status_code == 201, resp.text
    ingredient = resp.json()
    assert ingredient["name"] == "Amoxicillin"

    # Duplicate name is rejected.
    dup = client.post("/api/v1/active-ingredients", json={"name": "Amoxicillin"})
    assert dup.status_code == 409

    listed = client.get("/api/v1/active-ingredients")
    assert listed.status_code == 200
    assert any(i["id"] == ingredient["id"] for i in listed.json())

    # A drug can now reference the ingredient by id.
    drug = client.post(
        "/api/v1/drugs",
        json={
            "name": "Klamentin 500mg",
            "rx_class": "ETC",
            "base_unit": "viên",
            "ingredients": [{"ingredient_id": ingredient["id"], "amount": "500", "unit": "mg"}],
        },
    )
    assert drug.status_code == 201, drug.text
    assert drug.json()["ingredients"][0]["ingredient_id"] == ingredient["id"]


def test_stock_screen_reads_lots_then_labels_them_in_one_call(client: TestClient) -> None:
    """Đúng hai lượt gọi mà màn Tồn kho thực hiện (Sprint 10, D3).

    ① `GET /inventory/stock` — các lô còn hàng, cận hạn trước, chỉ có drug_id.
    ② `GET /drugs?ids=…` — gắn tên cho đúng các id của trang đó, MỘT lượt.

    Test này là chỗ duy nhất chứng minh hai đầu khớp nhau: nếu inventory đổi tên
    trường hoặc catalog bỏ lọc ids thì màn hình hiện UUID, và chỉ có bài kiểm
    này nói ra trước khi khách hàng nhìn thấy.
    """
    drug = client.post(
        "/api/v1/drugs",
        json={"name": "Cefixim 200mg", "rx_class": "ETC", "base_unit": "viên"},
    ).json()
    other = client.post(
        "/api/v1/drugs",
        json={"name": "Loratadin 10mg", "rx_class": "OTC", "base_unit": "viên"},
    ).json()

    for lot, days, qty in (("LO-XA", 400, "30"), ("LO-GAN", 30, "12")):
        r = client.post(
            "/api/v1/inventory/receive",
            json={
                "drug_id": drug["id"],
                "lot_no": lot,
                "expiry_date": (date.today() + timedelta(days=days)).isoformat(),
                "quantity": qty,
                "cost_price": "1000",
            },
        )
        assert r.status_code == 201, r.text

    stock = client.get("/api/v1/inventory/stock")
    assert stock.status_code == 200, stock.text
    rows = stock.json()

    assert [r["lot_no"] for r in rows] == ["LO-GAN", "LO-XA"]  # cận hạn lên trước
    assert Decimal(rows[0]["quantity"]) == Decimal("12.000")

    ids = sorted({r["drug_id"] for r in rows})
    labelled = client.get("/api/v1/drugs", params={"ids": ids})
    assert labelled.status_code == 200, labelled.text
    names = {d["id"]: d["name"] for d in labelled.json()}

    assert names == {drug["id"]: "Cefixim 200mg"}
    assert other["id"] not in names  # chỉ hỏi id của trang, không kéo cả danh mục


def test_stock_search_by_partial_name(client: TestClient) -> None:
    client.post(
        "/api/v1/drugs", json={"name": "Paracetamol 500mg", "rx_class": "OTC", "base_unit": "viên"}
    )
    client.post(
        "/api/v1/drugs", json={"name": "Ibuprofen 400mg", "rx_class": "OTC", "base_unit": "viên"}
    )

    found = client.get("/api/v1/drugs", params={"search": "para"})

    assert found.status_code == 200, found.text
    assert [d["name"] for d in found.json()] == ["Paracetamol 500mg"]
