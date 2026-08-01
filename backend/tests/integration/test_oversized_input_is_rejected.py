"""Chuỗi dài quá độ rộng cột phải bị từ chối 422 ở cổng vào — không được rơi xuống DB.

Trước bản vá, đúng các request dưới đây trả **500** trên Postgres
(``StringDataRightTruncationError``) trong khi toàn bộ suite vẫn xanh, vì SQLite bỏ
qua độ dài khai báo của ``varchar``. Bộ test này chạy được trên SQLite là nhờ chặn ở
tầng Pydantic — validate xảy ra **trước** khi chạm DB, nên nó bắt đúng cái nó cần bắt
dù nền dưới là gì (PROJECT_STATE §7aq).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
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
    db_path = tmp_path / "oversized.db"
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


def _too_long(column_width: int) -> str:
    return "A" * (column_width + 1)


def test_customer_name_and_phone_over_column_width_are_422(client: TestClient) -> None:
    over_name = client.post("/api/v1/customers", json={"full_name": _too_long(255)})
    assert over_name.status_code == 422, over_name.text

    over_phone = client.post(
        "/api/v1/customers", json={"full_name": "Nguyễn Văn A", "phone": _too_long(32)}
    )
    assert over_phone.status_code == 422, over_phone.text


def test_drug_fields_over_column_width_are_422(client: TestClient) -> None:
    base = {"name": "Paracetamol", "base_unit": "vien", "rx_class": "OTC"}
    for field, width in (
        ("name", 255),
        ("base_unit", 32),
        ("registration_no", 64),
        ("atc_code", 16),
        ("barcode", 64),
    ):
        resp = client.post("/api/v1/drugs", json={**base, field: _too_long(width)})
        assert resp.status_code == 422, f"{field}: {resp.status_code} {resp.text}"


def test_supplier_contact_fields_over_column_width_are_422(client: TestClient) -> None:
    for field, width in (("name", 255), ("tax_code", 32), ("phone", 32), ("email", 255)):
        resp = client.post("/api/v1/suppliers", json={"name": "NCC", **{field: _too_long(width)}})
        assert resp.status_code == 422, f"{field}: {resp.status_code} {resp.text}"


def test_lot_no_over_column_width_is_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/inventory/receive",
        json={
            "drug_id": str(uuid4()),
            "lot_no": _too_long(64),
            "expiry_date": (date.today() + timedelta(days=365)).isoformat(),
            "quantity": 10,
            "cost_price": 1000,
        },
    )
    assert resp.status_code == 422, resp.text


def test_values_at_exactly_the_column_width_still_pass_validation(client: TestClient) -> None:
    """Chặn đúng mức, không chặn thừa: dài bằng đúng độ rộng cột vẫn phải qua."""
    resp = client.post("/api/v1/customers", json={"full_name": "A" * 255})
    assert resp.status_code == 201, resp.text
