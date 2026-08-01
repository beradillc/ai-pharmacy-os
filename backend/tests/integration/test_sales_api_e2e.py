"""End-to-end HTTP test for the sales module (routing, DI, dev context, DB)."""

from __future__ import annotations

from collections.abc import Iterator
from decimal import Decimal
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
    db_path = tmp_path / "sales_api.db"
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


# 🔴 Từ 2026-07-31 `POST /sales` từ chối `drug_id` không có trong danh mục (phương án B,
# PROJECT_STATE §7co). Trước đó các test ở tệp này bán `uuid4()` ngẫu nhiên — chúng khai
# thác đúng sự khoan dung vừa bị bịt. Tạo thuốc THẬT thay vì nới cổng: một test bán mã
# thuốc không thể tồn tại thì phép khẳng định của nó cũng không nói về hệ thống thật.
def _drug(client: TestClient, *, rx: bool = False) -> str:
    """Tạo thuốc thật. `rx_class` phải khớp cờ `requires_prescription` của đơn.

    🔴 Trước 31/07 các test ETC ở đây đi qua nhánh *"unknown drug — trust the caller"*:
    thuốc không có trong danh mục nên máy chủ tin cờ của máy khách. Nay danh mục là nguồn
    quyền uy, nên một thuốc OTC bán kèm cờ `requires_prescription=true` **không** còn là
    đơn ETC — và đó là hành vi đúng, không phải hồi quy.
    """
    r = client.post(
        "/api/v1/drugs",
        json={
            "name": f"Thuốc-{uuid4().hex[:6]}",
            "rx_class": "ETC" if rx else "OTC",
            "base_unit": "viên",
        },
    )
    assert r.status_code == 201, r.text
    drug_id: str = r.json()["id"]
    return drug_id


def _payload(
    client: TestClient, client_uuid: str, *, rx: bool = False, rx_ref: str | None = None
) -> dict[str, object]:
    return {
        "client_uuid": client_uuid,
        "lines": [
            {
                "drug_id": _drug(client, rx=rx),
                "quantity": "2",
                "unit_price": "10000",
                "requires_prescription": rx,
            }
        ],
        "payments": [{"method": "CASH", "amount": "20000"}],
        "prescription_ref": rx_ref,
    }


def _validated_prescription(client: TestClient) -> str:
    """Create a prescription and validate it; return its id (status VALIDATED)."""
    created = client.post(
        "/api/v1/prescriptions",
        json={
            "customer_id": str(uuid4()),
            "doctor_name": "BS Nguyễn",
            "items": [
                {
                    "drug_id": str(uuid4()),
                    "quantity": "1",
                    "dose": "1 viên",
                    "frequency": "2 lần/ngày",
                    "duration": "5 ngày",
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    rx_id = str(created.json()["id"])
    validated = client.post(f"/api/v1/prescriptions/{rx_id}/validate")
    assert validated.status_code == 200, validated.text
    assert validated.json()["status"] == "VALIDATED"
    return rx_id


def test_create_sale_then_read_back(client: TestClient) -> None:
    resp = client.post("/api/v1/sales", json=_payload(client, "pos-1"))
    assert resp.status_code == 201, resp.text
    sale = resp.json()
    assert sale["status"] == "COMPLETED"
    assert sale["subtotal"] == "20000.00"

    got = client.get(f"/api/v1/sales/{sale['id']}")
    assert got.status_code == 200
    assert got.json()["id"] == sale["id"]


def test_sync_is_idempotent(client: TestClient) -> None:
    first = client.post("/api/v1/sync/sales", json=_payload(client, "offline-1"))
    assert first.status_code == 200, first.text
    second = client.post("/api/v1/sync/sales", json=_payload(client, "offline-1"))
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]  # no duplicate order


def test_etc_without_prescription_rejected(client: TestClient) -> None:
    resp = client.post("/api/v1/sales", json=_payload(client, "etc-1", rx=True))
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_etc_with_validated_prescription_allowed(client: TestClient) -> None:
    rx_ref = _validated_prescription(client)
    resp = client.post("/api/v1/sales", json=_payload(client, "etc-2", rx=True, rx_ref=rx_ref))
    assert resp.status_code == 201, resp.text


def test_etc_with_unknown_prescription_ref_rejected(client: TestClient) -> None:
    # A ref that is not a real prescription for the tenant is no longer accepted (S5.4).
    resp = client.post(
        "/api/v1/sales", json=_payload(client, "etc-3", rx=True, rx_ref=str(uuid4()))
    )
    assert resp.status_code == 422, resp.text


def test_empty_lines_rejected_by_schema(client: TestClient) -> None:
    resp = client.post("/api/v1/sales", json={"client_uuid": "x", "lines": [], "payments": []})
    assert resp.status_code == 422


def test_get_receipt_json_default(client: TestClient) -> None:
    sale = client.post("/api/v1/sales", json=_payload(client, "receipt-json-1")).json()
    resp = client.get(f"/api/v1/sales/{sale['id']}/receipt")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["order_id"] == sale["id"]
    assert body["subtotal"] == "20000.00"
    assert body["change_amount"] == "0.00"
    assert len(body["lines"]) == 1


def test_get_receipt_thermal_k80(client: TestClient) -> None:
    sale = client.post("/api/v1/sales", json=_payload(client, "receipt-thermal-1")).json()
    resp = client.get(f"/api/v1/sales/{sale['id']}/receipt", params={"format": "thermal_k80"})
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/plain")
    text = resp.text
    # 🔴 KHÔNG khẳng định tên nhà thuốc. `OrgSettings` đọc từ biến môi trường / `.env`, nên
    # khẳng định `"Nhà thuốc" in text` là khẳng định về **máy đang chạy test**, không phải về
    # sản phẩm. Nó đỏ ngay khi ai đó đặt `ORG__PHARMACY_NAME` cho một cơ sở thật — đúng điều
    # xảy ra 01/08 khi dựng CSDL Quầy thuốc 650.
    #
    # Thứ test này thật sự cần canh: bản in **có đủ ba phần bắt buộc của một hoá đơn** —
    # tiêu đề cơ sở (dòng đầu không rỗng), phần tiền, và chỗ ký.
    assert text.splitlines()[0].strip() != ""  # có tên cơ sở, bất kể tên gì
    assert "Ký tên:" in text
    assert "Tổng cộng:" in text


def test_get_receipt_pdf_a5_and_a4(client: TestClient) -> None:
    sale = client.post("/api/v1/sales", json=_payload(client, "receipt-pdf-1")).json()
    for fmt in ("pdf_a5", "pdf_a4"):
        resp = client.get(f"/api/v1/sales/{sale['id']}/receipt", params={"format": fmt})
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF")


def test_get_receipt_unknown_order_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/sales/{uuid4()}/receipt")
    assert resp.status_code == 404


def test_register_return_partial_then_full(client: TestClient) -> None:
    sale = client.post("/api/v1/sales", json=_payload(client, "return-1")).json()
    line_id = sale["lines"][0]["id"]

    partial = client.post(
        f"/api/v1/sales/{sale['id']}/returns", json={"line_id": line_id, "quantity": "1"}
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["status"] == "PARTIALLY_RETURNED"
    assert Decimal(partial.json()["lines"][0]["returned_quantity"]) == Decimal("1.000")

    full = client.post(
        f"/api/v1/sales/{sale['id']}/returns", json={"line_id": line_id, "quantity": "1"}
    )
    assert full.status_code == 200, full.text
    assert full.json()["status"] == "RETURNED"


def test_register_return_over_quantity_rejected(client: TestClient) -> None:
    sale = client.post("/api/v1/sales", json=_payload(client, "return-2")).json()
    line_id = sale["lines"][0]["id"]

    resp = client.post(
        f"/api/v1/sales/{sale['id']}/returns", json={"line_id": line_id, "quantity": "999"}
    )
    assert resp.status_code == 422


def test_register_return_unknown_order_404(client: TestClient) -> None:
    resp = client.post(
        f"/api/v1/sales/{uuid4()}/returns", json={"line_id": str(uuid4()), "quantity": "1"}
    )
    assert resp.status_code == 404


def test_list_sales_no_params_returns_todays_orders(client: TestClient) -> None:
    """`GET /sales` không tham số trả về đơn vừa tạo, mới nhất trước (Sprint 10, D1).

    🔴 PHẠM VI, đọc trước khi tin: test này KHÔNG chứng minh cửa sổ mặc định đúng
    bằng **một ngày**. Đơn tạo trong test luôn là hôm nay, nên một mặc định rộng
    hơn (7 ngày, 30 ngày) cũng làm nó xanh y hệt. Cái nó chứng minh là: không
    tham số thì có kết quả, đúng thứ tự, đúng hình dạng. Chứng minh biên một ngày
    cần một đơn mang ``created_at`` của hôm qua, mà ``created_at`` do CSDL đặt —
    ghi ra đây thay vì để câu docstring nói quá (đúng họ lỗi A-06).
    """
    created = [
        client.post("/api/v1/sales", json=_payload(client, f"list-{i}")).json() for i in range(3)
    ]

    resp = client.get("/api/v1/sales")
    assert resp.status_code == 200, resp.text
    rows = resp.json()

    assert {r["id"] for r in rows} == {c["id"] for c in created}
    # Không khẳng định một cặp cụ thể: created_at là now() phân giải 1 giây trên
    # SQLite, nên ba đơn liền nhau có thể cùng mốc (xem test_sales_list.py).
    keys = [(r["created_at"], r["id"]) for r in rows]
    assert keys == sorted(keys, reverse=True)
    assert rows[0]["line_count"] == 1
    assert rows[0]["subtotal"] == "20000.00"
    assert rows[0]["paid_total"] == "20000.00"
    assert "lines" not in rows[0]  # danh sách KHÔNG kéo theo từng dòng hàng


def test_list_sales_window_excludes_other_days(client: TestClient) -> None:
    client.post("/api/v1/sales", json=_payload(client, "win-1"))

    empty = client.get("/api/v1/sales", params={"date_from": "2020-01-01", "date_to": "2020-01-02"})
    assert empty.status_code == 200
    assert empty.json() == []


def test_list_sales_rejects_reversed_range(client: TestClient) -> None:
    resp = client.get("/api/v1/sales", params={"date_from": "2026-01-02", "date_to": "2026-01-01"})
    assert resp.status_code == 422, resp.text
