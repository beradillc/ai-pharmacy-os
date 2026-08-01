"""Sơ đồ kho qua HTTP thật — nối dây, mã lỗi, và phân quyền.

Vì sao cần tầng này ngoài test miền: miền chỉ biết dựng cây trong bộ nhớ. Bốn thứ chỉ ở
đây mới đỏ được, và ba trong bốn là chỗ đã hỏng thật trong dự án này trước đây:

* route có được **đăng ký** không, hay chỉ tồn tại trong tệp router (§7cn, cảnh báo dị ứng);
* trùng mã ở **hai cha khác nhau** có thật sự đi qua không — ràng buộc CSDL dễ siết quá tay;
* mã lỗi ra đúng **409/422/404** hay bị nuốt thành 500;
* thứ tự trả về có phải **thứ tự đi lấy hàng** không.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
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
    db_path = tmp_path / "location_e2e.db"
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


def _tao(client: TestClient, **body: Any) -> Any:
    return client.post("/api/v1/locations", json=body)


def _kho(client: TestClient, code: str = "KHO1") -> str:
    r = _tao(client, kind="WAREHOUSE", code=code)
    assert r.status_code == 201, r.text
    loc_id: str = r.json()["id"]
    return loc_id


def test_tao_kho_goc(client: TestClient) -> None:
    r = _tao(client, kind="WAREHOUSE", code="kho1", name="Kho chính")
    assert r.status_code == 201, r.text
    assert r.json()["path"] == "KHO1"  # đã chuẩn hoá viết hoa
    assert r.json()["parent_id"] is None


def test_duong_dan_ghep_theo_ca_cay(client: TestClient) -> None:
    kho = _kho(client)
    khu = _tao(client, kind="ZONE", code="A", parent_id=kho).json()["id"]
    ke = _tao(client, kind="SHELF", code="A01", parent_id=khu).json()["id"]
    o = _tao(client, kind="BIN", code="03", parent_id=ke)
    assert o.status_code == 201, o.text
    assert o.json()["path"] == "KHO1/A/A01/03"


def test_TRUNG_MA_o_hai_cha_KHAC_nhau_la_HOP_LE(client: TestClient) -> None:
    """🔴 Phép kiểm quan trọng nhất của bước này.

    Ô "01" dưới kệ A và ô "01" dưới kệ B là hai chỗ khác nhau. Bắt nhà thuốc đặt mã duy
    nhất toàn kho là bắt họ bỏ đúng cách đánh số đang dán trên kệ — và một ràng buộc CSDL
    siết quá tay ở đây sẽ chỉ lộ ra khi họ đã nhập được nửa kho.
    """
    kho = _kho(client)
    ke_a = _tao(client, kind="SHELF", code="A", parent_id=kho).json()["id"]
    ke_b = _tao(client, kind="SHELF", code="B", parent_id=kho).json()["id"]

    assert _tao(client, kind="BIN", code="01", parent_id=ke_a).status_code == 201
    r = _tao(client, kind="BIN", code="01", parent_id=ke_b)
    assert r.status_code == 201, r.text
    assert r.json()["path"] == "KHO1/B/01"


def test_trung_ma_CUNG_mot_cha_tra_409(client: TestClient) -> None:
    kho = _kho(client)
    _tao(client, kind="SHELF", code="A01", parent_id=kho)
    assert _tao(client, kind="SHELF", code="A01", parent_id=kho).status_code == 409


def test_trung_ma_giua_hai_KHO_GOC_cung_tra_409(client: TestClient) -> None:
    """🔴 Khoá duy nhất của CSDL KHÔNG bắt được ca này (NULL khác NULL trong chuẩn SQL).

    Chặn nằm ở tầng ứng dụng. Nếu ai đó bỏ phép kiểm `by_code_under` vì tưởng CSDL đã lo,
    test này phải đỏ.
    """
    _kho(client, "KHO1")
    assert _tao(client, kind="WAREHOUSE", code="KHO1").status_code == 409


def test_lop_goc_phai_la_KHO(client: TestClient) -> None:
    assert _tao(client, kind="SHELF", code="A01").status_code == 422


def test_dao_tang_tra_422(client: TestClient) -> None:
    kho = _kho(client)
    o = _tao(client, kind="BIN", code="01", parent_id=kho).json()["id"]
    assert _tao(client, kind="ZONE", code="A", parent_id=o).status_code == 422


def test_BO_TANG_thi_duoc(client: TestClient) -> None:
    """Nhà thuốc nhỏ chỉ dùng Kho → Kệ."""
    kho = _kho(client)
    assert _tao(client, kind="SHELF", code="A01", parent_id=kho).status_code == 201


def test_tang_khong_hop_le_tra_422_co_thong_diep_doc_duoc(client: TestClient) -> None:
    kho = _kho(client)
    r = _tao(client, kind="KE", code="A01", parent_id=kho)
    assert r.status_code == 422, r.text
    assert "KE" in r.json()["detail"]


def test_cha_khong_ton_tai_tra_404(client: TestClient) -> None:
    assert _tao(client, kind="SHELF", code="A01", parent_id=str(uuid4())).status_code == 404


def test_ma_chua_dau_gach_cheo_tra_422(client: TestClient) -> None:
    kho = _kho(client)
    assert _tao(client, kind="SHELF", code="A/01", parent_id=kho).status_code == 422


def test_danh_sach_sap_theo_THU_TU_LAY_HANG_khong_phai_bang_chu_cai(client: TestClient) -> None:
    """🔴 Kệ A01 và A02 có thể đối lưng nhau qua một lối đi — chỉ người xếp kho biết.

    Sắp theo bảng chữ cái là một phỏng đoán trông như tối ưu.
    """
    kho = _kho(client)
    _tao(client, kind="SHELF", code="A01", parent_id=kho, pick_order=9)
    _tao(client, kind="SHELF", code="Z99", parent_id=kho, pick_order=1)

    ds = client.get("/api/v1/locations").json()
    ma = [x["code"] for x in ds if x["kind"] == "SHELF"]
    assert ma == ["Z99", "A01"]


def test_doi_ten_KHONG_doi_ma(client: TestClient) -> None:
    kho = _kho(client)
    ke = _tao(client, kind="SHELF", code="A01", parent_id=kho, name="Kệ ho").json()["id"]
    r = client.patch(f"/api/v1/locations/{ke}", json={"name": "Kệ kháng sinh"})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Kệ kháng sinh"
    assert r.json()["code"] == "A01"
    assert r.json()["path"] == "KHO1/A01"


def test_ngung_hoat_dong_khi_CON_CHO_CON_tra_422(client: TestClient) -> None:
    kho = _kho(client)
    ke = _tao(client, kind="SHELF", code="A01", parent_id=kho).json()["id"]
    _tao(client, kind="BIN", code="01", parent_id=ke)

    r = client.patch(f"/api/v1/locations/{ke}", json={"is_active": False})
    assert r.status_code == 422, r.text


def test_ngung_hoat_dong_roi_thi_bien_khoi_danh_sach_mac_dinh(client: TestClient) -> None:
    kho = _kho(client)
    ke = _tao(client, kind="SHELF", code="A01", parent_id=kho).json()["id"]
    assert client.patch(f"/api/v1/locations/{ke}", json={"is_active": False}).status_code == 200

    mac_dinh = [x["id"] for x in client.get("/api/v1/locations").json()]
    assert ke not in mac_dinh

    day_du = [x["id"] for x in client.get("/api/v1/locations?include_inactive=true").json()]
    assert ke in day_du
