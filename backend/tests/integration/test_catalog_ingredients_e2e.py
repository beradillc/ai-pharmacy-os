"""End-to-end: sửa hoạt chất qua HTTP thật, và **cảnh báo dị ứng đổi theo ngay**.

Khác hai file kia và đó là lý do nó tồn tại:

* ``tests/unit/test_catalog_domain.py`` — đổi một list trong bộ nhớ
* ``tests/integration/test_catalog_replace_ingredients.py`` — service + CSDL, gọi Python
  trực tiếp
* file này — dựng app thật, gọi HTTP thật, rồi hỏi **đường cảnh báo dị ứng** xem nó có
  đổi hành vi không.

Hai lớp trên vẫn xanh được ngay cả khi route chưa nối vào app hoặc khi Pydantic lặng lẽ
bỏ mất một trường — đúng hình dạng lỗi kỷ luật #14 và #16 mô tả, và đúng lỗi đã lọt ở
tính năng dị ứng hôm 30/07 (``allergy_acknowledgement`` có ở input, thiếu ở request).

Phép kiểm đáng giá nhất ở đây không phải "PUT trả 200" mà là: **sửa hoạt chất xong,
``/sales/allergy-check`` đổi câu trả lời.** Đó là toàn bộ lý do tính năng này tồn tại.
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
    db_path = tmp_path / "catalog_ing_e2e.db"
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


def _ingredient(client: TestClient, name: str) -> str:
    r = client.post("/api/v1/active-ingredients", json={"name": f"{name}-{uuid4().hex[:6]}"})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _drug(client: TestClient, *ingredient_ids: str) -> str:
    r = client.post(
        "/api/v1/drugs",
        json={
            "name": f"Thuốc-{uuid4().hex[:6]}",
            "rx_class": "OTC",
            "base_unit": "viên",
            "ingredients": [
                {"ingredient_id": i, "amount": "500", "unit": "mg"} for i in ingredient_ids
            ],
        },
    )
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def _put(client: TestClient, drug_id: str, *ingredient_ids: str, amount: str = "500"):
    return client.put(
        f"/api/v1/drugs/{drug_id}/ingredients",
        json={
            "ingredients": [
                {"ingredient_id": i, "amount": amount, "unit": "mg"} for i in ingredient_ids
            ]
        },
    )


def _customer_di_ung(client: TestClient, ingredient_id: str) -> str:
    r = client.post("/api/v1/customers", json={"full_name": "Khách Thử", "phone": None})
    assert r.status_code == 201, r.text
    cid = str(r.json()["id"])
    r = client.post(
        f"/api/v1/customers/{cid}/consents", json={"purpose": "HEALTH", "granted": True}
    )
    assert r.status_code == 201, r.text
    r = client.post(
        f"/api/v1/customers/{cid}/allergies",
        json={"ingredient_id": ingredient_id, "severity": "SEVERE"},
    )
    assert r.status_code == 201, r.text
    return cid


def _so_canh_bao(client: TestClient, customer_id: str, drug_id: str) -> int:
    r = client.post(
        "/api/v1/sales/allergy-check", json={"customer_id": customer_id, "drug_ids": [drug_id]}
    )
    assert r.status_code == 200, r.text
    return int(r.json()["conflict_count"])


# --- điều thật sự đáng kiểm ---------------------------------------------------


def test_them_hoat_chat_thi_canh_bao_di_ung_BAT_DAU_KEU(client: TestClient) -> None:
    """🔴 Phép kiểm mạnh nhất của cả tính năng — chính là ca §7ce ngoài đời.

    Thuốc đã tạo mà không nối hoạt chất nào ⇒ khách dị ứng đi qua quầy trong im lặng.
    Sửa xong thì cảnh báo phải kêu **ngay**, không cần seed lại, không cần khởi động lại.
    """
    para = _ingredient(client, "Paracetamol")
    thuoc = _drug(client)  # cố ý KHÔNG hoạt chất nào
    khach = _customer_di_ung(client, para)
    assert _so_canh_bao(client, khach, thuoc) == 0  # im lặng, đúng như §7ce

    assert _put(client, thuoc, para).status_code == 200
    assert _so_canh_bao(client, khach, thuoc) == 1  # nay kêu


def test_bo_hoat_chat_thi_canh_bao_NGUNG_KEU(client: TestClient) -> None:
    """Chiều ngược lại — và đây chính là lý do hành động này phải vào sổ audit."""
    para = _ingredient(client, "Paracetamol")
    thuoc = _drug(client, para)
    khach = _customer_di_ung(client, para)
    assert _so_canh_bao(client, khach, thuoc) == 1

    assert _put(client, thuoc).status_code == 200  # danh sách rỗng
    assert _so_canh_bao(client, khach, thuoc) == 0


def test_sua_nham_sang_dung_thi_canh_bao_CHUYEN_theo(client: TestClient) -> None:
    """Dược sĩ nhập nhầm hoạt chất: cảnh báo phải thôi kêu ở người sai và kêu ở người đúng."""
    sai = _ingredient(client, "Ibuprofen")
    dung = _ingredient(client, "Paracetamol")
    thuoc = _drug(client, sai)
    khach_sai = _customer_di_ung(client, sai)
    khach_dung = _customer_di_ung(client, dung)
    assert _so_canh_bao(client, khach_sai, thuoc) == 1
    assert _so_canh_bao(client, khach_dung, thuoc) == 0

    assert _put(client, thuoc, dung).status_code == 200
    assert _so_canh_bao(client, khach_sai, thuoc) == 0
    assert _so_canh_bao(client, khach_dung, thuoc) == 1


# --- hợp đồng HTTP ------------------------------------------------------------


def test_thay_toan_bo_chu_khong_them_vao(client: TestClient) -> None:
    a, b, c = (_ingredient(client, x) for x in ("A", "B", "C"))
    thuoc = _drug(client, a, b)
    r = _put(client, thuoc, c)
    assert r.status_code == 200, r.text
    assert [i["ingredient_id"] for i in r.json()["ingredients"]] == [c]


def test_goi_hai_lan_cung_than_cho_cung_ket_qua(client: TestClient) -> None:
    """PUT là idempotent — đó là lý do chọn PUT chứ không PATCH."""
    a = _ingredient(client, "A")
    thuoc = _drug(client)
    lan_1 = _put(client, thuoc, a)
    lan_2 = _put(client, thuoc, a)
    assert lan_1.status_code == lan_2.status_code == 200
    assert lan_1.json()["ingredients"] == lan_2.json()["ingredients"]


def test_sua_ham_luong_giu_nguyen_hoat_chat(client: TestClient) -> None:
    a = _ingredient(client, "Amoxicillin")
    thuoc = _drug(client, a)
    r = _put(client, thuoc, a, amount="875")
    assert r.status_code == 200, r.text
    assert r.json()["ingredients"][0]["amount"] == "875"


def test_KHONG_ghi_de_ten_gia_ma_vach_qua_HTTP(client: TestClient) -> None:
    """Cổng hẹp, kiểm qua đúng đường người dùng đi."""
    ten = f"Tên-Gốc-{uuid4().hex[:6]}"
    ma_vach = f"BC{uuid4().hex[:10]}"
    r = client.post(
        "/api/v1/drugs",
        json={
            "name": ten,
            "rx_class": "ETC",
            "base_unit": "viên",
            "barcode": ma_vach,
            "sale_price": "12500",
        },
    )
    assert r.status_code == 201, r.text
    thuoc = str(r.json()["id"])
    assert _put(client, thuoc, _ingredient(client, "X")).status_code == 200

    sau = client.get(f"/api/v1/drugs/{thuoc}")
    assert sau.status_code == 200, sau.text
    assert sau.json()["name"] == ten
    assert sau.json()["barcode"] == ma_vach
    assert sau.json()["rx_class"] == "ETC"


def test_thieu_truong_ingredients_thi_422_khong_phai_xoa_sach(client: TestClient) -> None:
    """🔴 Body ``{}`` phải bị TỪ CHỐI, không được hiểu là "xoá hết".

    Nếu ``ingredients`` có giá trị mặc định, một lượt gọi hỏng sẽ xoá sạch hoạt chất mà
    trông như vô hại — và cảnh báo dị ứng của mã hàng đó tắt trong im lặng.
    """
    a = _ingredient(client, "A")
    thuoc = _drug(client, a)
    r = client.put(f"/api/v1/drugs/{thuoc}/ingredients", json={})
    assert r.status_code == 422, r.text
    assert len(client.get(f"/api/v1/drugs/{thuoc}").json()["ingredients"]) == 1


def test_thuoc_khong_ton_tai_thi_404(client: TestClient) -> None:
    assert _put(client, str(uuid4())).status_code == 404


def test_hoat_chat_khong_ton_tai_thi_404(client: TestClient) -> None:
    thuoc = _drug(client)
    assert _put(client, thuoc, str(uuid4())).status_code == 404


def test_trung_hoat_chat_thi_422(client: TestClient) -> None:
    a = _ingredient(client, "A")
    thuoc = _drug(client)
    assert _put(client, thuoc, a, a).status_code == 422


def test_ham_luong_khong_duong_thi_422(client: TestClient) -> None:
    a = _ingredient(client, "A")
    thuoc = _drug(client)
    assert _put(client, thuoc, a, amount="0").status_code == 422
