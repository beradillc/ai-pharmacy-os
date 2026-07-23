"""End-to-end: catalog's Rx classification governs whether a sale is allowed."""

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
    db_path = tmp_path / "rx_authority.db"
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


def _create_drug(client: TestClient, rx_class: str) -> str:
    r = client.post(
        "/api/v1/drugs",
        json={"name": f"Drug-{uuid4().hex[:6]}", "rx_class": rx_class, "base_unit": "viên"},
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _validated_prescription(client: TestClient) -> str:
    """Create + validate a prescription; return its id (status VALIDATED)."""
    created = client.post(
        "/api/v1/prescriptions",
        json={
            "customer_id": str(uuid4()),
            "doctor_name": "BS Trần",
            "items": [
                {
                    "drug_id": str(uuid4()),
                    "quantity": "1",
                    "dose": "1 viên",
                    "frequency": "1 lần/ngày",
                    "duration": "3 ngày",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    rx_id = str(created.json()["id"])
    validated = client.post(f"/api/v1/prescriptions/{rx_id}/validate")
    assert validated.status_code == 200, validated.text
    return rx_id


def _sale_body(
    client_uuid: str, drug_id: str, *, client_rx: bool, rx_ref: str | None = None
) -> dict[str, object]:
    return {
        "client_uuid": client_uuid,
        "lines": [
            {
                "drug_id": drug_id,
                "quantity": "1",
                "unit_price": "10000",
                "requires_prescription": client_rx,
            }
        ],
        "payments": [{"method": "CASH", "amount": "10000"}],
        "prescription_ref": rx_ref,
    }


def test_etc_drug_cannot_be_sold_as_otc(client: TestClient) -> None:
    etc = _create_drug(client, "ETC")
    # Client tries to pass it off as OTC with no prescription — catalog overrides.
    resp = client.post("/api/v1/sales", json=_sale_body("lie-1", etc, client_rx=False))
    assert resp.status_code == 422, resp.text


def test_etc_drug_sold_with_validated_prescription(client: TestClient) -> None:
    etc = _create_drug(client, "ETC")
    rx_ref = _validated_prescription(client)
    resp = client.post(
        "/api/v1/sales", json=_sale_body("ok-1", etc, client_rx=False, rx_ref=rx_ref)
    )
    assert resp.status_code == 201, resp.text


def test_etc_drug_blocked_when_prescription_ref_is_not_real(client: TestClient) -> None:
    etc = _create_drug(client, "ETC")
    # Catalog forces ETC; a bogus ref no longer satisfies the Rx rule (S5.4).
    resp = client.post(
        "/api/v1/sales", json=_sale_body("bad-1", etc, client_rx=False, rx_ref=str(uuid4()))
    )
    assert resp.status_code == 422, resp.text


def test_otc_drug_sold_despite_client_marking_rx(client: TestClient) -> None:
    otc = _create_drug(client, "OTC")
    # Catalog says OTC, so no prescription is required regardless of the flag.
    resp = client.post("/api/v1/sales", json=_sale_body("otc-1", otc, client_rx=True))
    assert resp.status_code == 201, resp.text
