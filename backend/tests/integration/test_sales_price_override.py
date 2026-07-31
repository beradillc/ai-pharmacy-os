"""Bán lệch giá niêm yết — cổng đòi lý do, qua HTTP thật (Chain chốt 2026-07-31).

Vì sao qua HTTP chứ không chỉ tầng service: đây là một cổng **cross-module** — `sales`
đọc giá niêm yết của `catalog` qua `DrugInfoProvider`, và sợi dây đó chỉ được nối ở
composition root. Ngày 31/07 đã có đúng một ca cùng hình dạng: cảnh báo dị ứng có đủ mã ở
cả ba module, ba lớp test dưới đều xanh, mà quầy **không hề gọi** endpoint nào — vì không
lớp nào chạy qua dây thật.
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
    db_path = tmp_path / "sales_price_override.db"
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


def _drug(client: TestClient, gia: str | None) -> str:
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


def _ban(client: TestClient, drug_id: str, don_gia: str, **extra: object):
    body: dict[str, object] = {
        "client_uuid": str(uuid4()),
        "lines": [
            {
                "drug_id": drug_id,
                "quantity": "1",
                "unit_price": don_gia,
                "requires_prescription": False,
            }
        ],
        "payments": [{"method": "CASH", "amount": don_gia}],
    }
    body.update(extra)
    return client.post("/api/v1/sales", json=body)


def test_ban_dung_gia_niem_yet_di_thang(client: TestClient) -> None:
    drug_id = _drug(client, "10000")
    r = _ban(client, drug_id, "10000")
    assert r.status_code == 201, r.text


def test_ban_CAO_hon_gia_niem_yet_ma_khong_co_ly_do_bi_tu_choi(client: TestClient) -> None:
    """Điều 6.5.i cấm bán cao hơn giá niêm yết. Chain chốt: cho bán, nhưng phải ghi lý do."""
    drug_id = _drug(client, "10000")
    r = _ban(client, drug_id, "12000")
    assert r.status_code == 422, r.text


def test_ban_THAP_hon_gia_niem_yet_ma_khong_co_ly_do_cung_bi_tu_choi(client: TestClient) -> None:
    """Chain chọn phương án ĐỐI XỨNG — khuyến mãi cũng phải ghi lý do."""
    drug_id = _drug(client, "10000")
    r = _ban(client, drug_id, "8000")
    assert r.status_code == 422, r.text


def test_co_ly_do_thi_ban_duoc(client: TestClient) -> None:
    drug_id = _drug(client, "10000")
    r = _ban(client, drug_id, "8000", price_override_reason="Khuyến mãi khách quen")
    assert r.status_code == 201, r.text


def test_ly_do_toan_khoang_trang_khong_tinh(client: TestClient) -> None:
    drug_id = _drug(client, "10000")
    r = _ban(client, drug_id, "8000", price_override_reason="   ")
    assert r.status_code == 422, r.text


def test_thuoc_CHUA_dat_gia_niem_yet_KHONG_bi_coi_la_lech(client: TestClient) -> None:
    """🔴 Không có giá niêm yết thì không có gì để lệch.

    Đòi thu ngân giải thích một phép so không tồn tại là vô nghĩa — và nó sẽ chặn đúng
    những mã vừa nhập từ nhà phân phối, chưa kịp chốt giá.
    """
    drug_id = _drug(client, None)
    r = _ban(client, drug_id, "7000")
    assert r.status_code == 201, r.text


def test_gia_12000_va_12000_chan_la_CUNG_mot_gia(client: TestClient) -> None:
    """Chuẩn hoá 2 chữ số thập phân — nếu so bằng chuỗi thì đây là một dương tính giả."""
    drug_id = _drug(client, "12000")
    r = _ban(client, drug_id, "12000.00")
    assert r.status_code == 201, r.text
