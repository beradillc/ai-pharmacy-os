"""End-to-end: cảnh báo dị ứng đi hết chuỗi thật — catalog → crm → clinical → sales.

Khác hẳn hai file test kia và đó là lý do nó tồn tại:

* ``tests/unit/test_allergy_risk_provider.py`` — adapter, với crm/clinical **giả**
* ``tests/integration/test_sales_allergy_gate.py`` — cổng ở ``complete_sale``, với
  provider **giả**
* file này — **không có gì giả**. Dựng app thật, tạo hoạt chất thật, thuốc thật, khách
  thật với đồng ý thật và dị ứng thật, rồi gọi HTTP thật.

Ba lớp trên chứng minh ba mệnh đề khác nhau. Hai lớp đầu vẫn xanh được ngay cả khi
composition root nối dây sai — đúng hình dạng lỗi mà kỷ luật #14 và #15 mô tả. Chỉ lớp
này bắt được việc quên truyền ``allergy_risk`` xuống ``register_sales``.
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
    db_path = tmp_path / "allergy_e2e.db"
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


def _ingredient(client: TestClient, name: str) -> str:
    r = client.post("/api/v1/active-ingredients", json={"name": name})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _drug(client: TestClient, ingredient_id: str | None) -> str:
    body: dict[str, object] = {
        "name": f"Thuốc-{uuid4().hex[:6]}",
        "rx_class": "OTC",
        "base_unit": "viên",
    }
    if ingredient_id is not None:
        body["ingredients"] = [{"ingredient_id": ingredient_id, "amount": "500", "unit": "mg"}]
    r = client.post("/api/v1/drugs", json=body)
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _customer(client: TestClient, *, health_consent: bool) -> str:
    r = client.post("/api/v1/customers", json={"full_name": "Khách Thử", "phone": None})
    assert r.status_code == 201, r.text
    cid = str(r.json()["id"])
    if health_consent:
        r = client.post(
            f"/api/v1/customers/{cid}/consents",
            json={"purpose": "HEALTH", "granted": True},
        )
        assert r.status_code == 201, r.text
    return cid


def _allergy(client: TestClient, customer_id: str, ingredient_id: str, severity: str) -> None:
    r = client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        json={"ingredient_id": ingredient_id, "severity": severity},
    )
    assert r.status_code == 201, r.text


def _sale_body(drug_id: str, customer_id: str, ack: str | None = None) -> dict[str, object]:
    body: dict[str, object] = {
        "client_uuid": uuid4().hex,
        "lines": [
            {
                "drug_id": drug_id,
                "quantity": "1",
                "unit_price": "10000",
                "requires_prescription": False,
            }
        ],
        "payments": [{"method": "CASH", "amount": "10000"}],
        "customer_id": customer_id,
    }
    if ack is not None:
        body["allergy_acknowledgement"] = ack
    return body


# --- Đ-7: hỏi trước khi bán --------------------------------------------------


def test_hoi_truoc_khi_ban_bao_dung_xung_dot(client: TestClient) -> None:
    """🔴 Phép kiểm mạnh nhất của cả tính năng: đi hết chuỗi, không mảnh nào giả."""
    ing = _ingredient(client, f"Paracetamol-{uuid4().hex[:6]}")
    drug = _drug(client, ing)
    cust = _customer(client, health_consent=True)
    _allergy(client, cust, ing, "SEVERE")

    r = client.post("/api/v1/sales/allergy-check", json={"customer_id": cust, "drug_ids": [drug]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["checked"] is True
    assert body["consent_granted"] is True
    assert body["conflict_count"] == 1
    assert body["worst_severity"] == "SEVERE"


def test_khach_khong_di_ung_thi_bao_DA_KIEM_VA_SACH(client: TestClient) -> None:
    ing = _ingredient(client, f"Ibuprofen-{uuid4().hex[:6]}")
    drug = _drug(client, ing)
    cust = _customer(client, health_consent=True)  # có đồng ý, không khai dị ứng nào

    r = client.post("/api/v1/sales/allergy-check", json={"customer_id": cust, "drug_ids": [drug]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["checked"] is True
    assert body["consent_granted"] is True
    assert body["conflict_count"] == 0


def test_chua_dong_y_thi_bao_PHEP_KIEM_KHONG_CHAY(client: TestClient) -> None:
    """🔴 Khác biệt sống còn: giao diện phải phân biệt được "sạch" với "không được xem".

    Cùng trả `conflict_count=0` như ca trên, nhưng `consent_granted=False`. Gộp hai
    trạng thái này lại là hệ thống nói dối người dùng.
    """
    ing = _ingredient(client, f"Cetirizin-{uuid4().hex[:6]}")
    drug = _drug(client, ing)
    cust = _customer(client, health_consent=False)

    r = client.post("/api/v1/sales/allergy-check", json={"customer_id": cust, "drug_ids": [drug]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["checked"] is True
    assert body["consent_granted"] is False
    assert body["conflict_count"] == 0


def test_khach_khong_ton_tai_thi_checked_false(client: TestClient) -> None:
    drug = _drug(client, None)
    r = client.post(
        "/api/v1/sales/allergy-check",
        json={"customer_id": str(uuid4()), "drug_ids": [drug]},
    )
    assert r.status_code == 200, r.text
    assert r.json()["checked"] is False


# --- Đ-6: cưỡng chế lúc hoàn tất ---------------------------------------------


def test_ban_khong_ghi_ly_do_bi_chan_422(client: TestClient) -> None:
    ing = _ingredient(client, f"Aspirin-{uuid4().hex[:6]}")
    drug = _drug(client, ing)
    cust = _customer(client, health_consent=True)
    _allergy(client, cust, ing, "MODERATE")

    r = client.post("/api/v1/sales", json=_sale_body(drug, cust))
    assert r.status_code == 422, r.text
    assert "MODERATE" in r.text


def test_ban_co_ghi_ly_do_thi_qua(client: TestClient) -> None:
    ing = _ingredient(client, f"Amoxicilin-{uuid4().hex[:6]}")
    drug = _drug(client, ing)
    cust = _customer(client, health_consent=True)
    _allergy(client, cust, ing, "SEVERE")

    r = client.post(
        "/api/v1/sales",
        json=_sale_body(drug, cust, ack="Bác sĩ đã chỉ định, khách dùng nhiều lần không sao"),
    )
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "COMPLETED"


def test_khach_khong_di_ung_thi_ban_binh_thuong(client: TestClient) -> None:
    """Cổng không được chặn nhầm đơn sạch — đây là ca chạy nhiều nhất ngoài đời."""
    ing = _ingredient(client, f"VitaminC-{uuid4().hex[:6]}")
    drug = _drug(client, ing)
    cust = _customer(client, health_consent=True)

    r = client.post("/api/v1/sales", json=_sale_body(drug, cust))
    assert r.status_code == 201, r.text


def test_chua_dong_y_thi_van_ban_duoc(client: TestClient) -> None:
    """Đ-10 qua đường HTTP thật: không phạt khách vì họ chưa đồng ý."""
    ing = _ingredient(client, f"Loratadin-{uuid4().hex[:6]}")
    drug = _drug(client, ing)
    cust = _customer(client, health_consent=False)
    r = client.post("/api/v1/sales", json=_sale_body(drug, cust))
    assert r.status_code == 201, r.text
