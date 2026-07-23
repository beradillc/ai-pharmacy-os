"""End-to-end HTTP test for the prescription module (routing, DI, dev context, DB)."""

from __future__ import annotations

from collections.abc import Iterator
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
    db_path = tmp_path / "prescription_api.db"
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


def _payload() -> dict[str, object]:
    return {
        "customer_id": str(uuid4()),
        "doctor_name": "BS. Lê Văn C",
        "items": [
            {
                "drug_id": str(uuid4()),
                "quantity": "10",
                "dose": "1 viên",
                "frequency": "2 lần/ngày",
                "duration": "5 ngày",
            }
        ],
    }


def test_create_prescription_then_read_back(client: TestClient) -> None:
    resp = client.post("/api/v1/prescriptions", json=_payload())
    assert resp.status_code == 201, resp.text
    rx = resp.json()
    assert rx["status"] == "DRAFT"

    got = client.get(f"/api/v1/prescriptions/{rx['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == rx["id"]


def test_validate_then_dispense(client: TestClient) -> None:
    created = client.post("/api/v1/prescriptions", json=_payload()).json()

    validated = client.post(f"/api/v1/prescriptions/{created['id']}/validate")
    assert validated.status_code == 200, validated.text
    assert validated.json()["status"] == "VALIDATED"

    dispensed = client.post(f"/api/v1/prescriptions/{created['id']}/dispense")
    assert dispensed.status_code == 200, dispensed.text
    assert dispensed.json()["status"] == "DISPENSED"


def test_dispense_without_validation_rejected(client: TestClient) -> None:
    created = client.post("/api/v1/prescriptions", json=_payload()).json()
    resp = client.post(f"/api/v1/prescriptions/{created['id']}/dispense")
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_reject_from_draft(client: TestClient) -> None:
    created = client.post("/api/v1/prescriptions", json=_payload()).json()
    resp = client.post(
        f"/api/v1/prescriptions/{created['id']}/reject", json={"reason": "Đơn không hợp lệ"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REJECTED"
    assert resp.json()["rejection_reason"] == "Đơn không hợp lệ"


def test_empty_items_rejected_by_schema(client: TestClient) -> None:
    body = _payload()
    body["items"] = []
    resp = client.post("/api/v1/prescriptions", json=body)
    assert resp.status_code == 422


def test_get_unknown_prescription_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/prescriptions/{uuid4()}")
    assert resp.status_code == 404
