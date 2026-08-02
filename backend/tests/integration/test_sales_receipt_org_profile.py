"""Đầu trang hoá đơn đọc **bản khai của cơ sở**, không đọc biến môi trường (nợ N-1).

Xem `docs/adr/ADR-0004-hoa-don-doc-thong-tin-co-so-da-khai.md`.

🔴 Vì sao có tệp riêng thay vì thêm vào `test_sales_api_e2e.py`: tệp đó cố ý **KHÔNG**
khẳng định gì về tên nhà thuốc, và chú thích của nó giải thích rất đúng lý do — tên đến từ
biến môi trường nên mọi khẳng định về nó là khẳng định về *máy đang chạy test*. Bản vá N-1
đổi chính điều đó: tên nay đến từ **CSDL của tenant**, tức từ thứ test tự dựng được. Đó là
lý do khẳng định ở đây có căn cứ còn ở đó thì không — và là lý do không nên trộn hai loại
vào một tệp.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.config import (
    AppSettings,
    DatabaseSettings,
    OrgSettings,
    SecuritySettings,
    Settings,
)
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.sales.domain import OrgProfile
from pharmacy_os.modules.sales.interface.router import _hoa_hai_nguon
from tests.conftest import urls_csdl_thu

#: Giá trị môi trường cố ý **khác hẳn** bản khai, để không mệnh đề nào xanh nhờ trùng nhau.
_MOI_TRUONG = OrgSettings(
    pharmacy_name="TỪ-BIẾN-MÔI-TRƯỜNG",
    address="ĐỊA-CHỈ-MÔI-TRƯỜNG",
    phone="0000000000",
    tax_code="9999999999",
)


# ─────────────────────────── phép hợp nhất, thuần ───────────────────────────


def test_chua_khai_gi_thi_lui_ve_moi_truong() -> None:
    """`None` = cơ sở vừa cài đặt, chưa ai vào màn Cài đặt. Hoá đơn vẫn phải in được."""
    assert _hoa_hai_nguon(_MOI_TRUONG, None) == _MOI_TRUONG


def test_khai_du_thi_ban_khai_thang_het() -> None:
    ket_qua = _hoa_hai_nguon(
        _MOI_TRUONG,
        OrgProfile(
            ten_co_so="Quầy thuốc 650",
            dia_chi="xã Thạnh Trị, Vĩnh Long",
            dien_thoai="0918280650",
            ma_so_thue="5800001234",
        ),
    )
    assert ket_qua.pharmacy_name == "Quầy thuốc 650"
    assert ket_qua.address == "xã Thạnh Trị, Vĩnh Long"
    assert ket_qua.phone == "0918280650"
    assert ket_qua.tax_code == "5800001234"


def test_tron_theo_TUNG_TRUONG_khong_lay_tron_mot_ben() -> None:
    """🔴 Mệnh đề đắt nhất của bản vá này.

    Một cơ sở mới khai tên và địa chỉ, **chưa có** mã số thuế. Nếu lấy trọn bản khai thì tờ
    hoá đơn **mất dòng MST đang in đúng từ trước** — một bước lùi im lặng, không mã lỗi nào,
    và chỉ lộ ra khi có người soi lại tờ giấy. Đúng loại lỗi kỷ luật #17 gọi là *"hình dạng
    không đổi nhưng ngữ nghĩa đổi"*.
    """
    ket_qua = _hoa_hai_nguon(
        _MOI_TRUONG,
        OrgProfile(
            ten_co_so="Quầy thuốc 650",
            dia_chi="xã Thạnh Trị, Vĩnh Long",
            dien_thoai="",
            ma_so_thue="",
        ),
    )
    assert ket_qua.pharmacy_name == "Quầy thuốc 650"  # đã khai ⇒ thắng
    assert ket_qua.address == "xã Thạnh Trị, Vĩnh Long"  # đã khai ⇒ thắng
    assert ket_qua.phone == "0000000000"  # bỏ trống ⇒ giữ giá trị cũ
    assert ket_qua.tax_code == "9999999999"  # bỏ trống ⇒ giữ giá trị cũ


# ─────────────────────────── đi hết đường, qua HTTP ───────────────────────────


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "receipt_org.db"
    _sync_url, _async_url = urls_csdl_thu(db_path)
    sync_engine = create_engine(_sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=_async_url),
        security=SecuritySettings(allow_dev_auth=True),
        org=_MOI_TRUONG,
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _thuoc(client: TestClient) -> str:
    """Thuốc THẬT trong danh mục — từ 31/07 `POST /sales` từ chối `drug_id` lạ (§7co)."""
    resp = client.post(
        "/api/v1/drugs",
        json={"name": "Thuốc kiểm thử N-1", "rx_class": "OTC", "base_unit": "viên"},
    )
    assert resp.status_code == 201, resp.text
    drug_id: str = resp.json()["id"]
    return drug_id


def _ban_mot_don(client: TestClient) -> str:
    drug_id = _thuoc(client)
    resp = client.post(
        "/api/v1/sales",
        json={
            "client_uuid": "n1-org-receipt-1",
            "lines": [
                {
                    "drug_id": drug_id,
                    "quantity": "1",
                    "unit_price": "1000",
                    "requires_prescription": False,
                }
            ],
            "payments": [{"method": "CASH", "amount": "1000"}],
        },
    )
    assert resp.status_code in (200, 201), resp.text
    sale_id: str = resp.json()["id"]
    return sale_id


def test_chua_khai_thi_hoa_don_in_theo_moi_truong(client: TestClient) -> None:
    """Hành vi CŨ vẫn còn nguyên khi tenant chưa khai gì — không ai bị mất tính năng."""
    sale_id = _ban_mot_don(client)
    text = client.get(f"/api/v1/sales/{sale_id}/receipt", params={"format": "thermal_k80"}).text
    assert "TỪ-BIẾN-MÔI-TRƯỜNG" in text
    assert "9999999999" in text


def test_da_khai_thi_hoa_don_in_theo_ban_khai(client: TestClient) -> None:
    """🔴 Mệnh đề đóng N-1: khai trên màn Cài đặt ⇒ tờ hoá đơn TIẾP THEO in theo giá trị mới.

    Đi đúng đường người dùng đi: `PUT /compliance/tenant-config` là thứ màn *Cài đặt →
    Thông tin cơ sở* gọi. Ghi thẳng vào CSDL thì test sẽ xanh kể cả khi endpoint hỏng.
    """
    sale_id = _ban_mot_don(client)

    resp = client.put(
        "/api/v1/compliance/tenant-config",
        json={
            "ma_co_so_ban_le": "68-01234",
            "ten_co_so": "Quầy thuốc 650",
            "dia_chi": "xã Thạnh Trị, Vĩnh Long",
            "dien_thoai": "0918280650",
            "ma_so_thue": "5800001234",
        },
    )
    assert resp.status_code in (200, 201), resp.text

    text = client.get(f"/api/v1/sales/{sale_id}/receipt", params={"format": "thermal_k80"}).text
    assert "Quầy thuốc 650" in text
    assert "xã Thạnh Trị, Vĩnh Long" in text
    assert "0918280650" in text
    assert "5800001234" in text
    # Và giá trị môi trường phải BIẾN MẤT — nếu còn, nghĩa là hoá đơn đang in cả hai
    # nguồn chồng lên nhau, một lỗi trông "gần đúng" nên rất dễ lọt.
    assert "TỪ-BIẾN-MÔI-TRƯỜNG" not in text
    assert "9999999999" not in text
