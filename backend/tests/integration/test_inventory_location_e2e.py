"""Tồn theo vị trí qua HTTP thật (BERAS V2 Phase 2).

Vì sao qua HTTP: đây là điểm nối **cross-module** — `inventory` đọc sơ đồ của `location`
qua một port, và sợi dây đó chỉ được nối ở composition root. Ngày 31/07 đã có đúng một ca
cùng hình dạng: mã đủ ở cả ba module, ba lớp test dưới đều xanh, mà quầy **không hề gọi**
endpoint nào — vì không lớp nào chạy qua dây thật.

Ba tính chất tệp này canh:

* **bất biến hai sổ** — xếp vào ô không bao giờ vượt tồn của lô;
* **hàng chưa xếp ô hiện ra được**, không bị giấu;
* **FEFO thắng** khi tra vị trí lấy hàng, dù ô đó đi xa hơn.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "inv_loc_e2e.db"
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


def _drug(client: TestClient) -> str:
    r = client.post(
        "/api/v1/drugs",
        json={"name": f"Thuốc-{uuid4().hex[:6]}", "rx_class": "OTC", "base_unit": "viên"},
    )
    assert r.status_code == 201, r.text
    drug_id: str = r.json()["id"]
    return drug_id


def _nhan(client: TestClient, drug_id: str, *, qty: str, hsd: date, lot: str) -> str:
    r = client.post(
        "/api/v1/inventory/receive",
        json={
            "drug_id": drug_id,
            "lot_no": lot,
            "expiry_date": hsd.isoformat(),
            "quantity": qty,
            "cost_price": "1000",
        },
    )
    assert r.status_code == 201, r.text
    batch_id: str = r.json()["batch_id"]
    return batch_id


def _o(client: TestClient, *, code: str, pick: int, parent: str | None = None) -> str:
    r = client.post(
        "/api/v1/locations",
        json={
            "kind": "WAREHOUSE" if parent is None else "BIN",
            "code": code,
            "parent_id": parent,
            "pick_order": pick,
        },
    )
    assert r.status_code == 201, r.text
    loc_id: str = r.json()["id"]
    return loc_id


def _cat(client: TestClient, batch: str, loc: str, qty: str) -> Any:
    return client.post(
        "/api/v1/inventory/put-away",
        json={"batch_id": batch, "location_id": loc, "quantity": qty},
    )


def test_cat_hang_vao_o_va_hien_so_CHUA_XEP(client: TestClient) -> None:
    """Giấu con số "chưa xếp" là để người vừa cất hàng tưởng đã xong."""
    d = _drug(client)
    lo = _nhan(client, d, qty="100", hsd=date.today() + timedelta(days=200), lot="L1")
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)

    r = _cat(client, lo, o, "30")
    assert r.status_code == 201, r.text
    assert r.json()["chua_xep_o"] == "70.000"
    assert r.json()["location_path"] == "KHO/A01"


def test_cat_VUOT_ton_cua_lo_tra_422(client: TestClient) -> None:
    """🔴 Bất biến hai sổ. Vỡ nó là màn lấy hàng chỉ người ta tới một ô không có hàng."""
    d = _drug(client)
    lo = _nhan(client, d, qty="10", hsd=date.today() + timedelta(days=200), lot="L1")
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)

    assert _cat(client, lo, o, "10").status_code == 201
    assert _cat(client, lo, o, "1").status_code == 422


def test_cat_hai_dot_vao_CUNG_mot_o_thi_CONG_DON(client: TestClient) -> None:
    """Nhận hàng hai đợt là bình thường — gán đè sẽ nuốt mất đợt trước trong im lặng."""
    d = _drug(client)
    lo = _nhan(client, d, qty="100", hsd=date.today() + timedelta(days=200), lot="L1")
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)

    _cat(client, lo, o, "30")
    r = _cat(client, lo, o, "20")
    assert r.status_code == 201, r.text
    assert r.json()["chua_xep_o"] == "50.000"

    ton_o = client.get(f"/api/v1/inventory/locations/{o}/stock").json()
    assert [x["quantity"] for x in ton_o] == ["50.000"]


def test_MOT_LO_trai_NHIEU_O(client: TestClient) -> None:
    d = _drug(client)
    lo = _nhan(client, d, qty="100", hsd=date.today() + timedelta(days=200), lot="L1")
    kho = _o(client, code="KHO", pick=0)
    a = _o(client, code="A01", pick=1, parent=kho)
    b = _o(client, code="B01", pick=2, parent=kho)

    assert _cat(client, lo, a, "60").status_code == 201
    assert _cat(client, lo, b, "40").status_code == 201

    cho = client.get(f"/api/v1/inventory/where?drug_id={d}").json()
    assert {c["location_path"] for c in cho} == {"KHO/A01", "KHO/B01"}


def test_FEFO_THANG_du_o_do_di_XA_hon(client: TestClient) -> None:
    """🔴 Quyết định của GĐ, đo qua dây thật: an toàn thuốc trước, đường đi sau."""
    d = _drug(client)
    han_xa = _nhan(client, d, qty="50", hsd=date.today() + timedelta(days=400), lot="XA")
    han_gan = _nhan(client, d, qty="50", hsd=date.today() + timedelta(days=30), lot="GAN")

    kho = _o(client, code="KHO", pick=0)
    o_gan = _o(client, code="A01", pick=1, parent=kho)  # đi thứ 1
    o_xa = _o(client, code="Z99", pick=99, parent=kho)  # đi thứ 99

    _cat(client, han_xa, o_gan, "50")  # hạn xa, NHƯNG ở ô đi gần
    _cat(client, han_gan, o_xa, "50")  # hạn gần, ở ô đi xa

    cho = client.get(f"/api/v1/inventory/where?drug_id={d}").json()
    assert cho[0]["lot_no"] == "GAN"
    assert cho[0]["location_path"] == "KHO/Z99"


def test_o_da_NGUNG_khong_cat_hang_vao_duoc(client: TestClient) -> None:
    d = _drug(client)
    lo = _nhan(client, d, qty="10", hsd=date.today() + timedelta(days=200), lot="L1")
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)
    assert client.patch(f"/api/v1/locations/{o}", json={"is_active": False}).status_code == 200

    assert _cat(client, lo, o, "5").status_code == 422


def test_thuoc_CHUA_XEP_O_nao_thi_where_tra_RONG(client: TestClient) -> None:
    """🔴 Rỗng ở đây KHÁC HẲN "kho hết hàng" — màn hình phải nói ra sự khác biệt đó."""
    d = _drug(client)
    _nhan(client, d, qty="100", hsd=date.today() + timedelta(days=200), lot="L1")
    assert client.get(f"/api/v1/inventory/where?drug_id={d}").json() == []


def test_o_khong_ton_tai_tra_404(client: TestClient) -> None:
    d = _drug(client)
    lo = _nhan(client, d, qty="10", hsd=date.today() + timedelta(days=200), lot="L1")
    assert _cat(client, lo, str(uuid4()), "1").status_code == 404


def test_lo_khong_ton_tai_tra_404(client: TestClient) -> None:
    kho = _o(client, code="KHO", pick=0)
    assert _cat(client, str(uuid4()), kho, "1").status_code == 404


def test_cat_hang_KHONG_doi_tong_ton(client: TestClient) -> None:
    """🔴 `TRANSFER` cố ý không đổi tổng tồn — hàng đã có từ lúc nhận."""
    d = _drug(client)
    lo = _nhan(client, d, qty="100", hsd=date.today() + timedelta(days=200), lot="L1")
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)

    truoc = client.get(f"/api/v1/inventory/on-hand?drug_id={d}").json()["on_hand"]
    _cat(client, lo, o, "40")
    sau = client.get(f"/api/v1/inventory/on-hand?drug_id={d}").json()["on_hand"]
    assert truoc == sau == "100.000"
