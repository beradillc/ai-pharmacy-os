"""`PUT /drugs/{id}/price` và `GET /drugs/{id}/price-history` — qua HTTP thật.

Vì sao cần tầng này ngoài test service: tầng service kiểm **quy tắc**, tầng này kiểm
**đường dây**. Ba thứ chỉ ở đây mới đỏ được, và cả ba đều là chỗ đã hỏng thật trong dự án
này trước đây (§7cn, cảnh báo dị ứng 31/07: mã đúng, nối dây thiếu, ba lớp test dưới vẫn
xanh):

* route có được **đăng ký** không, hay chỉ tồn tại trong tệp router;
* mã lỗi có ra đúng **422/404/403** không, hay bị nuốt thành 500;
* thân phản hồi có **hình dạng** frontend đang chờ không.
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


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "catalog_price_e2e.db"
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


def _drug(client: TestClient, gia: str | None = None) -> str:
    body: dict[str, object] = {
        "name": f"Thuốc-{uuid4().hex[:6]}",
        "rx_class": "OTC",
        "base_unit": "viên",
    }
    if gia is not None:
        body["sale_price"] = gia
    r = client.post("/api/v1/drugs", json=body)
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def test_dat_gia_lan_dau_tra_200_va_gia_moi(client: TestClient) -> None:
    drug_id = _drug(client)
    r = client.put(f"/api/v1/drugs/{drug_id}/price", json={"new_price": "12000"})
    assert r.status_code == 200, r.text
    assert r.json()["sale_price"] == "12000.00"


def test_doi_gia_thieu_ly_do_tra_422(client: TestClient) -> None:
    """Cưỡng chế THẬT nằm ở service — lược đồ không thấy được thuốc đã có giá hay chưa."""
    drug_id = _drug(client, gia="10000")
    r = client.put(f"/api/v1/drugs/{drug_id}/price", json={"new_price": "11000"})
    assert r.status_code == 422, r.text


def test_doi_gia_co_ly_do_tra_200(client: TestClient) -> None:
    drug_id = _drug(client, gia="10000")
    r = client.put(
        f"/api/v1/drugs/{drug_id}/price",
        json={"new_price": "11000", "reason": "Nhà phân phối tăng giá"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["sale_price"] == "11000.00"


def test_gia_am_bi_lUOC_DO_chan_truoc_khi_toi_service(client: TestClient) -> None:
    drug_id = _drug(client)
    r = client.put(f"/api/v1/drugs/{drug_id}/price", json={"new_price": "-1"})
    assert r.status_code == 422, r.text


def test_thuoc_khong_ton_tai_tra_404(client: TestClient) -> None:
    r = client.put(f"/api/v1/drugs/{uuid4()}/price", json={"new_price": "1000"})
    assert r.status_code == 404, r.text


def test_lich_su_tra_ve_moi_nhat_truoc_dung_hinh_dang(client: TestClient) -> None:
    """Hình dạng thân phản hồi là hợp đồng với frontend — đổi im lặng là hỏng im lặng."""
    drug_id = _drug(client)
    client.put(f"/api/v1/drugs/{drug_id}/price", json={"new_price": "1000"})
    client.put(f"/api/v1/drugs/{drug_id}/price", json={"new_price": "2000", "reason": "đợt 2"})

    r = client.get(f"/api/v1/drugs/{drug_id}/price-history")
    assert r.status_code == 200, r.text
    rows = r.json()
    assert [x["new_price"] for x in rows] == ["2000.00", "1000.00"]
    assert rows[0]["old_price"] == "1000.00"
    assert rows[0]["reason"] == "đợt 2"
    assert rows[1]["old_price"] is None  # lần ĐẦU đặt giá
    assert set(rows[0]) == {
        "id",
        "old_price",
        "new_price",
        "reason",
        "changed_by",
        "changed_at",
    }


def test_lich_su_cua_thuoc_chua_tung_doi_gia_la_rong(client: TestClient) -> None:
    drug_id = _drug(client)
    r = client.get(f"/api/v1/drugs/{drug_id}/price-history")
    assert r.status_code == 200, r.text
    assert r.json() == []
