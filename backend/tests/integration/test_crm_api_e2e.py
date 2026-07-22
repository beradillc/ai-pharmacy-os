"""End-to-end HTTP test for the crm module (routing, DI, DB) — single-module only,
no cross-module allergy check against clinical (that's a later, Opus-gated step).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pharmacy_os.core.config import AppSettings, DatabaseSettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.catalog.domain import ActiveIngredient
from pharmacy_os.modules.catalog.infrastructure.mappers import ingredient_to_orm

_PENICILLIN_ID = uuid4()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "crm_api.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    with Session(sync_engine) as session:
        session.add(ingredient_to_orm(ActiveIngredient(id=_PENICILLIN_ID, name="Penicillin")))
        session.commit()
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def test_create_customer_add_allergy_and_condition_round_trip(client: TestClient) -> None:
    created = client.post(
        "/api/v1/customers", json={"full_name": "Nguyễn Văn A", "phone": "0900000000"}
    )
    assert created.status_code == 201, created.text
    customer_id = created.json()["id"]

    with_allergy = client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        json={
            "ingredient_id": str(_PENICILLIN_ID),
            "severity": "SEVERE",
            "note": "Sốc phản vệ",
        },
    )
    assert with_allergy.status_code == 201, with_allergy.text
    assert with_allergy.json()["allergies"][0]["ingredient_id"] == str(_PENICILLIN_ID)

    with_condition = client.post(
        f"/api/v1/customers/{customer_id}/conditions",
        json={"condition_code": "E11", "note": "Đái tháo đường type 2"},
    )
    assert with_condition.status_code == 201, with_condition.text
    assert with_condition.json()["conditions"][0]["condition_code"] == "E11"

    fetched = client.get(f"/api/v1/customers/{customer_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert len(body["allergies"]) == 1
    assert len(body["conditions"]) == 1


def test_list_customers(client: TestClient) -> None:
    client.post("/api/v1/customers", json={"full_name": "Bình"})
    client.post("/api/v1/customers", json={"full_name": "An"})
    resp = client.get("/api/v1/customers")
    assert resp.status_code == 200
    assert [c["full_name"] for c in resp.json()] == ["An", "Bình"]


def test_get_unknown_customer_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/customers/{uuid4()}")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_duplicate_allergy_rejected_with_422(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json={"full_name": "C"})
    customer_id = created.json()["id"]
    client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        json={"ingredient_id": str(_PENICILLIN_ID), "severity": "MILD"},
    )
    again = client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        json={"ingredient_id": str(_PENICILLIN_ID), "severity": "SEVERE"},
    )
    assert again.status_code == 422, again.text
