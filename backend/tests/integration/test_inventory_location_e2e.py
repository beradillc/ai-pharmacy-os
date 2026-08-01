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

import json
from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from tests.conftest import urls_csdl_thu


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "inv_loc_e2e.db"


@pytest.fixture
def client(db_path: Path) -> Iterator[TestClient]:
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
    assert Decimal(r.json()["chua_xep_o"]) == Decimal("70.000")
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
    assert Decimal(r.json()["chua_xep_o"]) == Decimal("50.000")

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


# ─── Phase 5: nhận hàng gắn vị trí ngay ─────────────────────────────────────────


def _nhan_vao_o(client: TestClient, drug_id: str, *, qty: str, lot: str, loc: str | None) -> Any:
    body: dict[str, Any] = {
        "drug_id": drug_id,
        "lot_no": lot,
        "expiry_date": (date.today() + timedelta(days=200)).isoformat(),
        "quantity": qty,
        "cost_price": "1000",
    }
    if loc is not None:
        body["location_id"] = loc
    return client.post("/api/v1/inventory/receive", json=body)


def test_nhan_hang_GAN_O_NGAY_thi_quay_thay_cho_lay_lien(client: TestClient) -> None:
    """🔴 Điểm của cả Phase 5.

    Tách làm hai lượt gọi sẽ để lại một khoảng — vài phút hay vài ngày — mà hàng đã nằm
    trong sổ tồn nhưng chưa có địa chỉ. Người ra quầy trong khoảng đó được bảo *"chưa xếp
    ô"* dù hàng đang nằm ngay trên kệ.
    """
    d = _drug(client)
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)

    assert _nhan_vao_o(client, d, qty="50", lot="L1", loc=o).status_code == 201

    cho = client.get(f"/api/v1/inventory/where?drug_id={d}").json()
    assert [(c["location_path"], c["quantity"]) for c in cho] == [("KHO/A01", "50.000")]


def test_nhan_KHONG_gan_o_van_hop_le(client: TestClient) -> None:
    """Hàng vừa dỡ khỏi xe chưa chắc đã biết cất đâu — bắt chọn ô là bắt đoán."""
    d = _drug(client)
    assert _nhan_vao_o(client, d, qty="50", lot="L1", loc=None).status_code == 201
    assert client.get(f"/api/v1/inventory/where?drug_id={d}").json() == []


def test_nhan_vao_o_KHONG_TON_TAI_tra_404_va_KHONG_nhan_hang(client: TestClient) -> None:
    """Toàn-bộ-hoặc-không-gì: từ chối rồi vẫn nhận hàng là để lại hàng không ai biết."""
    d = _drug(client)
    assert _nhan_vao_o(client, d, qty="50", lot="L1", loc=str(uuid4())).status_code == 404
    assert Decimal(
        client.get(f"/api/v1/inventory/on-hand?drug_id={d}").json()["on_hand"]
    ) == Decimal("0.000")


def test_nhan_vao_o_DA_NGUNG_tra_422(client: TestClient) -> None:
    d = _drug(client)
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)
    client.patch(f"/api/v1/locations/{o}", json={"is_active": False})

    assert _nhan_vao_o(client, d, qty="50", lot="L1", loc=o).status_code == 422


# ─── Phase 9: khởi tạo tồn kho — KHÔNG phải nhập mua ─────────────────────────────


def test_khoi_tao_ton_ghi_ref_type_INIT_khong_phai_GRN(client: TestClient, db_path: Path) -> None:
    """🔴 Điểm của cả Phase 9.

    Hiệu ứng lên tồn kho giống hệt nhập mua, nhưng Ý NGHĨA khác: khởi tạo là kiểm đếm
    hàng đã có trên kệ, thường không biết giá vốn thật. Trộn hai thứ thì giá vốn 0 sẽ bị
    `merge_receipt` kéo vào bình quân gia quyền — một con số sai lặng lẽ, chỉ lộ ra ở báo
    cáo lãi gộp nhiều tháng sau.
    """
    d = _drug(client)
    r = client.post(
        "/api/v1/inventory/initialize",
        json={
            "drug_id": d,
            "lot_no": "INIT-1",
            "expiry_date": (date.today() + timedelta(days=300)).isoformat(),
            "quantity": "80",
            "cost_price": "0",
        },
    )
    assert r.status_code == 201, r.text
    assert Decimal(
        client.get(f"/api/v1/inventory/on-hand?drug_id={d}").json()["on_hand"]
    ) == Decimal("80.000")

    # 🔴 Đọc THẲNG sổ chuyển động. Chỉ khẳng định tồn kho thì test này xanh kể cả khi
    # `ref_type` không hề được đặt — đúng loại "xanh vì lý do sai" mà kỷ luật #14 canh.
    engine = create_engine(urls_csdl_thu(db_path)[0])
    with engine.connect() as conn:
        loai = (
            conn.execute(text("SELECT ref_type FROM stock_movements WHERE type='IN'"))
            .scalars()
            .all()
        )
    engine.dispose()
    assert loai == ["INIT"], f"ref_type phải là INIT, nhận {loai}"


def test_khoi_tao_ton_gan_o_ngay_duoc(client: TestClient) -> None:
    """Kiểm kê tổng thì vừa đếm vừa biết hàng nằm đâu — đó là cả điểm của việc đi kiểm."""
    d = _drug(client)
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)

    r = client.post(
        "/api/v1/inventory/initialize",
        json={
            "drug_id": d,
            "lot_no": "INIT-2",
            "expiry_date": (date.today() + timedelta(days=300)).isoformat(),
            "quantity": "12",
            "cost_price": "0",
            "location_id": o,
        },
    )
    assert r.status_code == 201, r.text
    cho = client.get(f"/api/v1/inventory/where?drug_id={d}").json()
    assert [(c["location_path"], c["quantity"]) for c in cho] == [("KHO/A01", "12.000")]


def test_nhap_mua_van_ghi_GRN(client: TestClient, db_path: Path) -> None:
    """🔴 Nới cho khởi tạo KHÔNG được đổi ý nghĩa của đường nhập mua."""
    d = _drug(client)
    assert _nhan_vao_o(client, d, qty="5", lot="MUA-1", loc=None).status_code == 201

    engine = create_engine(urls_csdl_thu(db_path)[0])
    with engine.connect() as conn:
        loai = (
            conn.execute(text("SELECT ref_type FROM stock_movements WHERE type='IN'"))
            .scalars()
            .all()
        )
    engine.dispose()
    assert loai == ["GRN"], f"nhập mua phải là GRN, nhận {loai}"


# ─── Phase 11: kiểm kê theo ô ────────────────────────────────────────────────────


def _o_co_hang(client: TestClient, *, qty: str, lot: str) -> tuple[str, str, str]:
    """Dựng: một thuốc, một lô đã nhận, một ô đã cất hàng vào. Trả (drug, batch, ô)."""
    d = _drug(client)
    kho = _o(client, code=f"K{uuid4().hex[:4]}", pick=0)
    o = _o(client, code=f"O{uuid4().hex[:4]}", pick=1, parent=kho)
    r = client.post(
        "/api/v1/inventory/receive",
        json={
            "drug_id": d,
            "lot_no": lot,
            "expiry_date": (date.today() + timedelta(days=300)).isoformat(),
            "quantity": qty,
            "cost_price": "1000",
            "location_id": o,
        },
    )
    assert r.status_code == 201, r.text
    return d, r.json()["batch_id"], o


def test_kiem_ke_tron_vong_duyet_thi_ton_kho_MOI_doi(client: TestClient) -> None:
    """🔴 Mệnh đề trung tâm của Phase 11.

    Nộp phiên **không** đụng tồn kho — chỉ duyệt mới đụng. Con số đếm được là một lời khai
    cho tới lúc có người chịu trách nhiệm ký vào nó.
    """
    d, lo, o = _o_co_hang(client, qty="10", lot=f"KK{uuid4().hex[:4]}")

    phien = client.post("/api/v1/inventory/counts", json={"location_id": o})
    assert phien.status_code == 201, phien.text
    pid = phien.json()["id"]
    assert phien.json()["status"] == "DANG_DEM"

    # Đếm được 7, sổ ghi 10 → thiếu 3.
    r = client.post(
        f"/api/v1/inventory/counts/{pid}/lines", json={"batch_id": lo, "counted_qty": "7"}
    )
    assert r.status_code == 200, r.text
    # Chưa nộp ⇒ system_qty và lech phải là None, KHÔNG phải 0.
    assert r.json()["lines"][0]["system_qty"] is None
    assert r.json()["lines"][0]["lech"] is None

    r = client.post(f"/api/v1/inventory/counts/{pid}/submit")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "CHO_DUYET"
    assert Decimal(r.json()["lines"][0]["system_qty"]) == Decimal("10.000")
    assert r.json()["lines"][0]["lech"] == "-3.000"

    # 🔴 Nộp rồi mà tồn kho VẪN chưa đổi — đây là chỗ dễ code sai nhất.
    assert Decimal(
        client.get(f"/api/v1/inventory/on-hand?drug_id={d}").json()["on_hand"]
    ) == Decimal("10.000")

    r = client.post(f"/api/v1/inventory/counts/{pid}/approve")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "DA_DUYET"
    assert Decimal(
        client.get(f"/api/v1/inventory/on-hand?drug_id={d}").json()["on_hand"]
    ) == Decimal("7.000")

    # Sổ vị trí đi theo, không lệch với sổ tổng.
    trong_o = client.get(f"/api/v1/inventory/locations/{o}/stock").json()
    assert [x["quantity"] for x in trong_o] == ["7.000"]


def test_duyet_ghi_chuyen_dong_ADJUST_ref_COUNT(client: TestClient, db_path: Path) -> None:
    """MovementType.ADJUST tồn tại từ commit đầu và chưa từng được dùng — đây là lần đầu."""
    _, lo, o = _o_co_hang(client, qty="5", lot=f"AJ{uuid4().hex[:4]}")
    pid = client.post("/api/v1/inventory/counts", json={"location_id": o}).json()["id"]
    client.post(f"/api/v1/inventory/counts/{pid}/lines", json={"batch_id": lo, "counted_qty": "8"})
    client.post(f"/api/v1/inventory/counts/{pid}/submit")
    client.post(f"/api/v1/inventory/counts/{pid}/approve")

    engine = create_engine(urls_csdl_thu(db_path)[0])
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT type, ref_type, quantity FROM stock_movements WHERE type='ADJUST'")
        ).all()
    engine.dispose()
    assert len(rows) == 1
    assert rows[0][0] == "ADJUST"
    assert rows[0][1] == "COUNT"
    # So bằng SỐ, không bằng chuỗi: SQLite trả `3`, Postgres trả `3.000` cho cùng một
    # Numeric(18,3). Khẳng định trên chuỗi ở đây sẽ đỏ khi đổi nền mà sản phẩm không sai —
    # đúng lớp chênh lệch dialect mà kỷ luật #7 (bổ sung) canh.
    assert Decimal(str(rows[0][2])) == Decimal("3")  # đếm 8, sổ 5 → thừa 3


def test_tu_choi_thi_ton_kho_KHONG_doi(client: TestClient) -> None:
    d, lo, o = _o_co_hang(client, qty="10", lot=f"TC{uuid4().hex[:4]}")
    pid = client.post("/api/v1/inventory/counts", json={"location_id": o}).json()["id"]
    client.post(f"/api/v1/inventory/counts/{pid}/lines", json={"batch_id": lo, "counted_qty": "1"})
    client.post(f"/api/v1/inventory/counts/{pid}/submit")

    r = client.post(f"/api/v1/inventory/counts/{pid}/reject")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "TU_CHOI"
    assert Decimal(
        client.get(f"/api/v1/inventory/on-hand?drug_id={d}").json()["on_hand"]
    ) == Decimal("10.000")


def test_dong_KHOP_khong_sinh_chuyen_dong_nao(client: TestClient, db_path: Path) -> None:
    """Ghi một ADJUST bằng 0 vào sổ chỉ-ghi-thêm là rác vĩnh viễn."""
    _, lo, o = _o_co_hang(client, qty="6", lot=f"KH{uuid4().hex[:4]}")
    pid = client.post("/api/v1/inventory/counts", json={"location_id": o}).json()["id"]
    client.post(f"/api/v1/inventory/counts/{pid}/lines", json={"batch_id": lo, "counted_qty": "6"})
    client.post(f"/api/v1/inventory/counts/{pid}/submit")
    client.post(f"/api/v1/inventory/counts/{pid}/approve")

    engine = create_engine(urls_csdl_thu(db_path)[0])
    with engine.connect() as conn:
        n = conn.execute(text("SELECT count(*) FROM stock_movements WHERE type='ADJUST'")).scalar()
    engine.dispose()
    assert n == 0


def test_da_nop_thi_khong_dem_them_duoc_409(client: TestClient) -> None:
    _, lo, o = _o_co_hang(client, qty="4", lot=f"NP{uuid4().hex[:4]}")
    pid = client.post("/api/v1/inventory/counts", json={"location_id": o}).json()["id"]
    client.post(f"/api/v1/inventory/counts/{pid}/lines", json={"batch_id": lo, "counted_qty": "4"})
    client.post(f"/api/v1/inventory/counts/{pid}/submit")

    r = client.post(
        f"/api/v1/inventory/counts/{pid}/lines", json={"batch_id": lo, "counted_qty": "9"}
    )
    assert r.status_code == 409, r.text


def test_khong_duyet_hai_lan_409(client: TestClient) -> None:
    _, lo, o = _o_co_hang(client, qty="4", lot=f"D2{uuid4().hex[:4]}")
    pid = client.post("/api/v1/inventory/counts", json={"location_id": o}).json()["id"]
    client.post(f"/api/v1/inventory/counts/{pid}/lines", json={"batch_id": lo, "counted_qty": "3"})
    client.post(f"/api/v1/inventory/counts/{pid}/submit")
    assert client.post(f"/api/v1/inventory/counts/{pid}/approve").status_code == 200
    assert client.post(f"/api/v1/inventory/counts/{pid}/approve").status_code == 409


def test_o_khong_ton_tai_thi_404(client: TestClient) -> None:
    r = client.post("/api/v1/inventory/counts", json={"location_id": str(uuid4())})
    assert r.status_code == 404, r.text


def test_danh_sach_loc_theo_trang_thai(client: TestClient) -> None:
    _, lo, o = _o_co_hang(client, qty="4", lot=f"DS{uuid4().hex[:4]}")
    pid = client.post("/api/v1/inventory/counts", json={"location_id": o}).json()["id"]

    dang_dem = client.get("/api/v1/inventory/counts?status=DANG_DEM").json()
    assert [p["id"] for p in dang_dem] == [pid]
    assert client.get("/api/v1/inventory/counts?status=CHO_DUYET").json() == []

    client.post(f"/api/v1/inventory/counts/{pid}/lines", json={"batch_id": lo, "counted_qty": "4"})
    client.post(f"/api/v1/inventory/counts/{pid}/submit")
    assert [p["id"] for p in client.get("/api/v1/inventory/counts?status=CHO_DUYET").json()] == [
        pid
    ]


# --- lộ trình lấy hàng cho CẢ GIỎ, qua dây thật (BERAS V2 Phase 4) -------------------


def _lo_trinh(client: TestClient, dong: list[dict[str, Any]]) -> Any:
    return client.post("/api/v1/inventory/pick-route", json={"dong": dong})


def test_lo_trinh_gop_HAI_MA_cung_o_thanh_MOT_chang(client: TestClient) -> None:
    """Cái tốn công là *đi tới ô*. Hai mã cùng ô ⇒ một chặng, hai dòng."""
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)
    d1, d2 = _drug(client), _drug(client)
    _cat(
        client,
        _nhan(client, d1, qty="10", hsd=date.today() + timedelta(days=300), lot="L1"),
        o,
        "10",
    )
    _cat(
        client,
        _nhan(client, d2, qty="10", hsd=date.today() + timedelta(days=300), lot="L2"),
        o,
        "10",
    )

    kq = _lo_trinh(
        client, [{"drug_id": d1, "quantity": "2"}, {"drug_id": d2, "quantity": "3"}]
    ).json()

    assert len(kq["chang"]) == 1
    assert len(kq["chang"][0]["dong"]) == 2
    assert kq["thieu"] == []


def test_lo_trinh_sap_theo_DUONG_DI(client: TestClient) -> None:
    """🔴 FEFO đã quyết xong ở bước chọn lô; lộ trình thì đi từ ô gần tới ô xa."""
    kho = _o(client, code="KHO", pick=0)
    o_gan = _o(client, code="A01", pick=1, parent=kho)
    o_xa = _o(client, code="Z99", pick=99, parent=kho)
    d_xa, d_gan = _drug(client), _drug(client)
    # Mã ở ô XA có hạn GẦN hơn — nếu sắp theo HSD thì nó phải đứng đầu, và đó là sai.
    _cat(
        client,
        _nhan(client, d_xa, qty="10", hsd=date.today() + timedelta(days=30), lot="G"),
        o_xa,
        "10",
    )
    _cat(
        client,
        _nhan(client, d_gan, qty="10", hsd=date.today() + timedelta(days=400), lot="X"),
        o_gan,
        "10",
    )

    kq = _lo_trinh(
        client, [{"drug_id": d_xa, "quantity": "1"}, {"drug_id": d_gan, "quantity": "1"}]
    ).json()

    assert [c["location_path"] for c in kq["chang"]] == ["KHO/A01", "KHO/Z99"]


def test_lo_trinh_MOT_MA_thieu_thi_VAN_tra_phan_lay_duoc(client: TestClient) -> None:
    """🔴 Một giỏ mười mã mà một mã chưa xếp ô thì người đi lấy VẪN CẦN chín mã kia.

    Khác `allocate_from_locations` (toàn-vẹn-hoặc-không, phục vụ một lượt xuất kho): ở đây
    bỏ trắng cả tờ vì một dòng là làm hỏng công việc của người đang đứng chờ.
    """
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)
    co = _drug(client)
    khong = _drug(client)  # nhận hàng nhưng KHÔNG xếp ô
    _cat(
        client,
        _nhan(client, co, qty="10", hsd=date.today() + timedelta(days=300), lot="L1"),
        o,
        "10",
    )
    _nhan(client, khong, qty="10", hsd=date.today() + timedelta(days=300), lot="L2")

    kq = _lo_trinh(
        client, [{"drug_id": co, "quantity": "1"}, {"drug_id": khong, "quantity": "1"}]
    ).json()

    assert len(kq["chang"]) == 1
    assert kq["thieu"] == [khong]


def test_lo_trinh_doi_hoi_it_nhat_MOT_dong(client: TestClient) -> None:
    assert _lo_trinh(client, []).status_code == 422


# --- tóm tắt tồn MỌI Ô, nguồn của sơ đồ trực quan (BERAS V2 Phase 12 mức 1) ----------


def test_tom_tat_gop_NHIEU_LO_trong_mot_o_thanh_MOT_dong(client: TestClient) -> None:
    """Sơ đồ hỏi *"ô này bận không"*, không hỏi *"ô này có những lô nào"*."""
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)
    d = _drug(client)
    _cat(
        client,
        _nhan(client, d, qty="10", hsd=date.today() + timedelta(days=100), lot="L1"),
        o,
        "10",
    )
    _cat(
        client, _nhan(client, d, qty="5", hsd=date.today() + timedelta(days=300), lot="L2"), o, "5"
    )

    kq = client.get("/api/v1/inventory/locations/summary").json()

    assert len(kq) == 1
    assert kq[0]["so_lo"] == 2
    assert Decimal(kq[0]["tong_so_luong"]) == Decimal("15")


def test_tom_tat_lay_HSD_GAN_NHAT_trong_o(client: TestClient) -> None:
    """🔴 Con số cảnh báo phải là cái SỚM NHẤT. Lấy trung bình hay lấy lô đầu tiên đều cho
    một ngày muộn hơn thực tế — và một cảnh báo muộn thì bằng không có."""
    kho = _o(client, code="KHO", pick=0)
    o = _o(client, code="A01", pick=1, parent=kho)
    d = _drug(client)
    gan = date.today() + timedelta(days=20)
    _cat(
        client,
        _nhan(client, d, qty="10", hsd=date.today() + timedelta(days=400), lot="XA"),
        o,
        "10",
    )
    _cat(client, _nhan(client, d, qty="5", hsd=gan, lot="GAN"), o, "5")

    kq = client.get("/api/v1/inventory/locations/summary").json()

    assert kq[0]["hsd_gan_nhat"] == gan.isoformat()


def test_tom_tat_KHONG_tra_o_TRONG(client: TestClient) -> None:
    """Ô trống không có dòng — màn hình biết chúng trống bằng cách đối chiếu với sơ đồ.

    "Không có dòng" rẻ hơn "dòng với số 0" cho một kho mà phần lớn ô trống.
    """
    kho = _o(client, code="KHO", pick=0)
    co = _o(client, code="A01", pick=1, parent=kho)
    _o(client, code="A02", pick=2, parent=kho)  # trống
    d = _drug(client)
    _cat(
        client,
        _nhan(client, d, qty="10", hsd=date.today() + timedelta(days=100), lot="L1"),
        co,
        "10",
    )

    kq = client.get("/api/v1/inventory/locations/summary").json()

    assert [r["location_id"] for r in kq] == [co]


def test_tom_tat_MOT_luot_goi_cho_NHIEU_o(client: TestClient) -> None:
    """Lý do endpoint này tồn tại: một kho vài trăm ô không được thành vài trăm lượt gọi."""
    kho = _o(client, code="KHO", pick=0)
    d = _drug(client)
    for i in range(3):
        o = _o(client, code=f"A0{i}", pick=i + 1, parent=kho)
        lo = _nhan(client, d, qty="10", hsd=date.today() + timedelta(days=100 + i), lot=f"L{i}")
        _cat(client, lo, o, "10")

    kq = client.get("/api/v1/inventory/locations/summary").json()

    assert len(kq) == 3


class TestDieuChinhTonNhanh:
    """``POST /inventory/adjust`` — điều chỉnh tồn một lô trong một lượt (UAT M-07).

    🔴 Mệnh đề trung tâm: đường tắt này **không phải một đường đổi tồn kho mới**. Nó chạy
    trọn luồng kiểm kê đã có, nên cả ba sổ (``stock_balances``, ``stock_at_location``,
    ``stock_movements``) phải đổi **y hệt** như khi đi đường dài bốn bước. Nếu có ngày ai
    đó "tối ưu" nó thành một lệnh UPDATE thẳng vào tồn, hai sổ sẽ lệch nhau im lặng — và
    chỉ lộ ra khi có người đứng trước một ô rỗng.
    """

    def test_dieu_chinh_mot_luot_doi_dung_ca_hai_so(self, client: TestClient) -> None:
        d, lo, o = _o_co_hang(client, qty="10", lot=f"DC{uuid4().hex[:4]}")

        r = client.post(
            "/api/v1/inventory/adjust",
            json={
                "location_id": o,
                "batch_id": lo,
                "actual_qty": "7",
                "reason": "Vỡ 3 hộp khi xếp kệ",
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["status"] == "DA_DUYET"

        # Sổ tổng đổi…
        assert Decimal(
            client.get(f"/api/v1/inventory/on-hand?drug_id={d}").json()["on_hand"]
        ) == Decimal("7.000")
        # …và sổ vị trí đi theo, không lệch.
        trong_o = client.get(f"/api/v1/inventory/locations/{o}/stock").json()
        assert [x["quantity"] for x in trong_o] == ["7.000"]

    def test_de_lai_mot_phieu_kiem_ke_tra_duoc(self, client: TestClient) -> None:
        """Mỗi lượt điều chỉnh để lại một phiếu — thứ thanh tra hỏi khi sổ khác thực tế."""
        _, lo, o = _o_co_hang(client, qty="4", lot=f"DP{uuid4().hex[:4]}")
        pid = client.post(
            "/api/v1/inventory/adjust",
            json={"location_id": o, "batch_id": lo, "actual_qty": "9", "reason": "Đếm lại"},
        ).json()["id"]

        phieu = client.get(f"/api/v1/inventory/counts/{pid}")
        assert phieu.status_code == 200
        assert phieu.json()["status"] == "DA_DUYET"
        assert Decimal(phieu.json()["lines"][0]["system_qty"]) == Decimal("4.000")
        assert phieu.json()["lines"][0]["lech"] == "5.000"

    def test_bat_buoc_co_ly_do(self, client: TestClient) -> None:
        """Không có lý do thì không có gì trả lời được câu *"vì sao tồn đổi"*.

        🔴 ``"   "`` (ba dấu cách) có mặt vì một lý do cụ thể: nó **lọt qua** ``min_length=3``
        của Pydantic và chỉ bị chặn ở tầng service. Bản đầu của test này chỉ thử ``""``,
        ``"  "``, ``"."`` — cả ba đều bị Pydantic từ chối, nên **xoá hẳn phép kiểm ở service
        vẫn xanh** (đo thật: `MUTANT2_EXIT=0`). Một test canh hai lớp phòng thủ mà chỉ chạm
        được lớp ngoài thì lớp trong không có gì canh nó.
        """
        _, lo, o = _o_co_hang(client, qty="4", lot=f"LD{uuid4().hex[:4]}")
        for ly_do in ["", "  ", ".", "   ", "\t\n "]:
            r = client.post(
                "/api/v1/inventory/adjust",
                json={"location_id": o, "batch_id": lo, "actual_qty": "3", "reason": ly_do},
            )
            assert r.status_code == 422, f"lý do {ly_do!r} lẽ ra phải bị từ chối: {r.text}"

    def test_audit_mang_ly_do_va_gia_tri_cu_moi(self, client: TestClient, db_path: Path) -> None:
        """Dòng audit phải mang ``reason`` + ``old_qty``/``new_qty``.

        🔴 Đây là **toàn bộ** giá trị của đường tắt về mặt truy vết: ``stock_movements`` ghi
        rằng tồn đã đổi, chỉ sổ audit trả lời được *vì sao*. Và cặp ``old_qty``/``new_qty``
        chính là thứ màn Nhật ký hiện thành cột "Thay đổi" (M-05) — bỏ nó đi thì cột ấy
        trống và không cổng nào từng biết.

        Bản đầu của bộ test này không khẳng định gì về audit, nên xoá hai dòng ghi
        ``old_qty``/``new_qty`` vẫn xanh trọn vẹn (đo thật: `MUTANT3_EXIT=0`).
        """
        _, lo, o = _o_co_hang(client, qty="6", lot=f"AU{uuid4().hex[:4]}")
        client.post(
            "/api/v1/inventory/adjust",
            json={"location_id": o, "batch_id": lo, "actual_qty": "2", "reason": "Hết hạn, huỷ 4"},
        )
        engine = create_engine(urls_csdl_thu(db_path)[0])
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT context FROM audit_logs WHERE action='INVENTORY_COUNT_APPROVED' "
                    "ORDER BY occurred_at DESC"
                )
            ).all()
        engine.dispose()
        # 🔴 ĐÚNG MỘT dòng, không phải hai. Bản đầu gọi `_record` thêm một lượt sau
        # `approve_count`, nên mỗi lượt điều chỉnh để lại HAI dòng `INVENTORY_COUNT_APPROVED`
        # cho cùng một việc — một dòng trần, một dòng có lý do. Không cổng nào đỏ (cả hai
        # đều là dòng hợp lệ), nhưng người soát sổ đếm gấp đôi số lượt duyệt và dòng trần
        # đọc như một lượt duyệt KHÔNG có lý do.
        assert len(rows) == 1, f"chờ đúng 1 dòng audit, có {len(rows)} — đang ghi trùng"
        ctx = json.loads(rows[0][0]) if isinstance(rows[0][0], str) else rows[0][0]
        assert ctx["reason"] == "Hết hạn, huỷ 4"
        assert Decimal(ctx["old_qty"]) == Decimal("6")
        assert Decimal(ctx["new_qty"]) == Decimal("2")
        # Thiết bị vẫn đi kèm — M-06 áp cho MỌI dòng audit, kể cả dòng mới thêm hôm nay.
        assert "user_agent" in ctx

    def test_so_thuc_te_am_bi_tu_choi(self, client: TestClient) -> None:
        _, lo, o = _o_co_hang(client, qty="4", lot=f"AM{uuid4().hex[:4]}")
        r = client.post(
            "/api/v1/inventory/adjust",
            json={"location_id": o, "batch_id": lo, "actual_qty": "-1", "reason": "thử"},
        )
        assert r.status_code == 422, r.text

    def test_ghi_chuyen_dong_ADJUST_y_het_duong_dai(
        self, client: TestClient, db_path: Path
    ) -> None:
        """Cùng ``MovementType.ADJUST`` / ``ref_type='COUNT'`` như đường bốn bước.

        Nếu đường tắt ghi một ``ref_type`` khác, mọi báo cáo đối chiếu tồn kho sẽ bỏ sót
        đúng những lượt điều chỉnh làm bằng đường tắt — mà đó lại là đa số.
        """
        _, lo, o = _o_co_hang(client, qty="5", lot=f"MV{uuid4().hex[:4]}")
        client.post(
            "/api/v1/inventory/adjust",
            json={"location_id": o, "batch_id": lo, "actual_qty": "8", "reason": "Tìm thấy thêm"},
        )
        engine = create_engine(urls_csdl_thu(db_path)[0])
        with engine.connect() as conn:
            # KHÔNG lọc theo `batch_id`: SQLite lưu UUID dạng hex **không dấu gạch**, nên so
            # với chuỗi có gạch thì không dòng nào khớp và test đỏ vì **phép đo** chứ không
            # phải sản phẩm (đã mất một lượt chạy vì đúng chuyện này). Cùng lớp chênh lệch
            # dialect mà kỷ luật #7 (bổ sung) canh — lọc theo `type` là dialect-trung-lập.
            rows = conn.execute(
                text("SELECT type, quantity, ref_type FROM stock_movements WHERE type='ADJUST'")
            ).all()
        engine.dispose()
        assert len(rows) == 1
        assert rows[0][0] == "ADJUST"
        # So bằng SỐ, không bằng chuỗi: SQLite trả `3`, Postgres trả `3.000`.
        assert Decimal(str(rows[0][1])) == Decimal("3")
        assert rows[0][2] == "COUNT"
