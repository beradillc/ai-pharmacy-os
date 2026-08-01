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
from tests.conftest import urls_csdl_thu


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "prescription_api.db"
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


def test_search_finds_prescriptions_without_an_image(client: TestClient) -> None:
    """Tra cứu (M-08) phải trả cả đơn **chưa chụp ảnh** — khác hẳn ``/archive``.

    🔴 Đây là toàn bộ lý do endpoint này tồn tại. Màn Lưu trữ đã có sẵn và chạy tốt, nên
    rất dễ kết luận *"đã tra cứu được đơn thuốc rồi"* — nhưng nó lọc ``image_data IS NOT
    NULL``. Khi thanh tra hỏi *"đơn thuốc của khách X"*, một đơn nhập tay không ảnh **vẫn
    là một đơn thật** và biến mất khỏi Lưu trữ mà không báo gì.
    """
    tao = client.post("/api/v1/prescriptions", json=_payload())
    assert tao.status_code == 201, tao.text
    rx = tao.json()

    luu_tru = client.get("/api/v1/prescriptions/archive")
    assert luu_tru.status_code == 200
    assert rx["id"] not in [r["id"] for r in luu_tru.json()], "Lưu trữ chỉ chứa đơn CÓ ảnh"

    tra_cuu = client.get("/api/v1/prescriptions")
    assert tra_cuu.status_code == 200, tra_cuu.text
    assert rx["id"] in [r["id"] for r in tra_cuu.json()]


def test_search_filters_by_customer_and_status(client: TestClient) -> None:
    """Bộ lọc phải THU HẸP thật, và thu hẹp đúng dòng.

    Một bộ lọc bị bỏ quên vẫn trả 200 và vẫn trả một danh sách — nó chỉ trả **nhầm**
    danh sách, và người dùng đọc kết quả của khách A tưởng là của khách B.
    """
    khach_a, khach_b = str(uuid4()), str(uuid4())
    a = client.post("/api/v1/prescriptions", json={**_payload(), "customer_id": khach_a}).json()
    b = client.post("/api/v1/prescriptions", json={**_payload(), "customer_id": khach_b}).json()

    chi_a = client.get("/api/v1/prescriptions", params={"customer_id": khach_a}).json()
    assert [r["id"] for r in chi_a] == [a["id"]]
    assert b["id"] not in [r["id"] for r in chi_a]

    # Cả hai đơn đang DRAFT ⇒ lọc DRAFT thấy cả hai, lọc VALIDATED không thấy đơn nào.
    draft = client.get("/api/v1/prescriptions", params={"status": "DRAFT"}).json()
    assert {a["id"], b["id"]} <= {r["id"] for r in draft}
    duyet = client.get("/api/v1/prescriptions", params={"status": "VALIDATED"}).json()
    assert [r["id"] for r in duyet] == []


def test_search_filters_by_date_range(client: TestClient) -> None:
    """Khoảng ngày phải cắt được cả hai đầu — một đầu quên thì màn hiện đúng nửa sự thật."""
    rx = client.post("/api/v1/prescriptions", json=_payload()).json()

    trong = client.get(
        "/api/v1/prescriptions",
        params={"created_from": "2000-01-01T00:00:00", "created_to": "2100-01-01T00:00:00"},
    ).json()
    assert rx["id"] in [r["id"] for r in trong]

    qua_khu = client.get(
        "/api/v1/prescriptions", params={"created_to": "2000-01-01T00:00:00"}
    ).json()
    assert [r["id"] for r in qua_khu] == []

    tuong_lai = client.get(
        "/api/v1/prescriptions", params={"created_from": "2100-01-01T00:00:00"}
    ).json()
    assert [r["id"] for r in tuong_lai] == []
