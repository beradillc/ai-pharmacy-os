"""HTTP-level wiring for the VNPAY endpoints (Sprint 8 mục 4/4).

No real ``payment_vnpay`` plugin is installed in this suite (that package is
tested separately, and against the real sandbox — see PROJECT_STATE), so
``PLUGINS__ENABLED`` is empty here, same as any deployment that has not turned
the gateway on. What this file proves is narrower but still worth pinning: the
routes are registered, reachable, wired through the container, and degrade the
way a misconfigured deployment should — not a 500. The full initiate → confirm
orchestration against a fake gateway is covered at the service layer in
``test_sales_vnpay_flow.py``.
"""

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
from tests.conftest import urls_csdl_thu


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "sales_vnpay_api.db"
    _sync_url, _async_url = urls_csdl_thu(db_path)
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


def _payload(client_uuid: str) -> dict[str, object]:
    return {
        "client_uuid": client_uuid,
        "lines": [
            {"drug_id": str(uuid4()), "quantity": "2", "unit_price": "10000"},
        ],
    }


def test_initiate_without_gateway_enabled_fails_clean_not_500(client: TestClient) -> None:
    resp = client.post("/api/v1/sales/vnpay/initiate", json=_payload("vnpay-api-1"))
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_callback_route_needs_no_auth_and_answers_vnpay_shape(client: TestClient) -> None:
    """The route itself must be reachable with **no** Authorization header — a
    webhook cannot present one. Gateway not configured ⇒ VNPAY RspCode 99, still
    a 200 (VNPAY reads the body, not the HTTP status)."""
    resp = client.get(
        "/api/v1/sales/vnpay/callback",
        params={"vnp_TxnRef": str(uuid4()), "vnp_ResponseCode": "00"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"RspCode": "99", "Message": "Unknown error"}


def test_callback_route_precedes_the_order_id_route(client: TestClient) -> None:
    """Route registration order matters: ``/sales/vnpay/callback`` must not be
    swallowed by ``GET /sales/{order_id}`` — a regression here would 422 on UUID
    parsing (``"vnpay"`` is not a valid order id) instead of reaching the handler."""
    resp = client.get("/api/v1/sales/vnpay/callback", params={"vnp_TxnRef": str(uuid4())})
    assert resp.status_code == 200
