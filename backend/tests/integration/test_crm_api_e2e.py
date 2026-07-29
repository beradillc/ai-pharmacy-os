"""End-to-end HTTP test for the crm module (routing, DI, DB) — single-module only,
no cross-module allergy check against clinical (that's a later, Opus-gated step).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.core.db import configure_field_encryption, reset_field_encryption
from pharmacy_os.core.security.crypto import KEY_BYTES, BlindIndex
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.catalog.domain import ActiveIngredient
from pharmacy_os.modules.catalog.infrastructure.mappers import ingredient_to_orm

_PENICILLIN_ID = uuid4()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "crm_api.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    with Session(sync_engine) as session:
        session.add(ingredient_to_orm(ActiveIngredient(id=_PENICILLIN_ID, name="Penicillin")))
        session.commit()
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
        security=SecuritySettings(allow_dev_auth=True),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _grant_health_consent(client: TestClient, customer_id: str) -> None:
    """Health data cannot be recorded without consent (Luật 91/2025 Điều 26.1)."""
    r = client.post(
        f"/api/v1/customers/{customer_id}/consents",
        json={"purpose": "HEALTH", "granted": True, "terms_version": "v1"},
    )
    assert r.status_code == 201, r.text


def test_create_customer_add_allergy_and_condition_round_trip(client: TestClient) -> None:
    created = client.post(
        "/api/v1/customers", json={"full_name": "Nguyễn Văn A", "phone": "0900000000"}
    )
    assert created.status_code == 201, created.text
    customer_id = created.json()["id"]
    _grant_health_consent(client, customer_id)

    with_allergy = client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        json={
            "ingredient_id": str(_PENICILLIN_ID),
            "severity": "SEVERE",
            "note": "Sốc phản vệ",
        },
    )
    assert with_allergy.status_code == 201, with_allergy.text
    assert with_allergy.json()["allergies"][0]["ingredient_id"] == str(_PENICILLIN_ID)

    with_condition = client.post(
        f"/api/v1/customers/{customer_id}/conditions",
        json={"condition_code": "E11", "note": "Đái tháo đường type 2"},
    )
    assert with_condition.status_code == 201, with_condition.text
    assert with_condition.json()["conditions"][0]["condition_code"] == "E11"

    fetched = client.get(f"/api/v1/customers/{customer_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert len(body["allergies"]) == 1
    assert len(body["conditions"]) == 1


def test_list_customers(client: TestClient) -> None:
    """Không còn khẳng định thứ tự bảng chữ cái: `full_name` nay là ciphertext
    (migration `0035`, Chain quyết 2026-07-28) nên `list()` sắp theo `created_at DESC,
    id`. Khẳng định ở đây là thứ kiểm được qua HTTP — trả đủ, không lặp."""
    client.post("/api/v1/customers", json={"full_name": "Bình"})
    client.post("/api/v1/customers", json={"full_name": "An"})

    resp = client.get("/api/v1/customers")

    assert resp.status_code == 200
    names = [c["full_name"] for c in resp.json()]
    assert sorted(names) == ["An", "Bình"]


def test_get_unknown_customer_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/customers/{uuid4()}")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")


def test_duplicate_allergy_rejected_with_422(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json={"full_name": "C"})
    customer_id = created.json()["id"]
    _grant_health_consent(client, customer_id)
    client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        json={"ingredient_id": str(_PENICILLIN_ID), "severity": "MILD"},
    )
    again = client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        json={"ingredient_id": str(_PENICILLIN_ID), "severity": "SEVERE"},
    )
    assert again.status_code == 422, again.text


def test_unknown_ingredient_id_rejected_with_404_not_500(client: TestClient) -> None:
    created = client.post("/api/v1/customers", json={"full_name": "D"})
    customer_id = created.json()["id"]
    _grant_health_consent(client, customer_id)
    resp = client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        json={"ingredient_id": str(uuid4()), "severity": "MILD"},
    )
    assert resp.status_code == 404, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")


# --- Tra khách theo SĐT (A1, docs/features/khach-hang-tich-diem) --------------


def test_tra_khach_theo_dung_so_dien_thoai(client: TestClient) -> None:
    created = client.post(
        "/api/v1/customers", json={"full_name": "Trần Thị Bích", "phone": "0912345678"}
    )
    assert created.status_code == 201, created.text

    res = client.get("/api/v1/customers", params={"phone": "0912345678"})
    assert res.status_code == 200, res.text
    assert [c["id"] for c in res.json()] == [created.json()["id"]]


def test_so_dien_thoai_khong_co_tra_DANH_SACH_RONG_chu_khong_phai_404(client: TestClient) -> None:
    """🔴 Màn Bán hàng gõ số điện thoại TỪNG CHỮ.

    "Chưa thấy ai" là trạng thái **bình thường** của mọi lần gõ dở, không phải
    lỗi. Trả 404 thì mỗi phím bấm sinh một dòng đỏ trong log và một thông báo lỗi
    nhấp nháy trước mặt thu ngân — rồi họ học cách bỏ qua thông báo lỗi.
    """
    res = client.get("/api/v1/customers", params={"phone": "0900000000"})
    assert res.status_code == 200, res.text
    assert res.json() == []


def test_tra_theo_SDT_khong_lam_lo_du_lieu_suc_khoe(client: TestClient) -> None:
    """Nhận diện ở quầy ≠ mở hồ sơ bệnh. Cùng lý do như `list_customers`."""
    created = client.post(
        "/api/v1/customers", json={"full_name": "Lê Văn Cường", "phone": "0987654321"}
    ).json()
    assert created["id"]

    row = client.get("/api/v1/customers", params={"phone": "0987654321"}).json()[0]
    assert row.get("allergies") in (None, [])
    assert row.get("conditions") in (None, [])


@pytest.fixture
def blind_index(client: TestClient) -> Iterator[None]:
    """Cài dấu vân tay tra cứu cho ĐÚNG test cần nó, rồi dọn sạch.

    🔴 `_blind_index` là **trạng thái toàn tiến trình** (`configure_field_encryption`).
    Bản đầu tôi viết test tra số điện thoại mà không cài gì — nó **xanh khi chạy
    riêng file, đỏ khi chạy cả bộ**, vì kết quả phụ thuộc test nào chạy trước đã
    để lại cái gì trong biến toàn cục đó. Một test đổi màu theo thứ tự chạy thì
    không chứng minh được gì cả.

    🔴 Và fixture này PHẢI nhận `client`. Không phải để dùng, mà để **chạy sau
    nó**: `create_app` gọi `configure_field_encryption` ở composition root, nên
    dựng app SAU khi cài dấu vân tay sẽ **xoá sạch** cái vừa cài. Lần sửa đầu tôi
    quên chỗ này — test xanh khi chạy nhóm crm, vẫn đỏ khi chạy cả bộ, và tôi suýt
    kết luận là "còn một test khác gây nhiễu".
    """
    configure_field_encryption(None, write_enabled=False, blind_index=BlindIndex(b"k" * KEY_BYTES))
    yield
    reset_field_encryption()


@pytest.mark.parametrize(
    "typed",
    ["0901112223", "  0901112223  ", "0901 112 223", "0901.112.223", "0901-112-223"],
)
@pytest.mark.usefixtures("blind_index")
def test_go_so_dien_thoai_kieu_nao_cung_ra(client: TestClient, typed: str) -> None:
    """Thu ngân gõ số điện thoại theo đủ kiểu — khách đọc sao thì họ gõ vậy.

    🔴 Công lao này KHÔNG phải của `.strip()` trong service. Nó là của
    `normalize_for_index` (NFKC + casefold + bỏ mọi ký tự không phải chữ-số) mà
    dấu vân tay dùng, nên `0901 112 223` băm ra cùng chuỗi với `0901112223`.
    Bản đầu tôi viết test này để canh `.strip()`, đột biến bỏ `.strip()` vẫn
    XANH — test mô tả sai thứ nó chứng minh. Nay nó canh đúng cái có thật, và
    canh rộng hơn: **cả năm cách gõ**, không riêng khoảng trắng thừa.

    🔴 Và chỉ đúng KHI DEPLOYMENT ĐÃ BẬT KHOÁ BĂM — nên fixture `blind_index`
    cài tường minh. Không có khoá thì repo so sánh cột thô, và `0901 112 223`
    KHÔNG tìm ra `0901112223`. Đó là một khoảng trống thật, đã ghi trong
    docstring `CrmService.find_customer_by_phone`; `config.py` cũng đã bắt buộc
    đặt `ENCRYPTION__BLIND_INDEX_KEY` ở môi trường thật vì đúng lý do này.

    (`.strip()` vẫn giữ trong service: nó là cái duy nhất còn tác dụng trên
    deployment chưa bật khoá băm.)
    """
    client.post("/api/v1/customers", json={"full_name": "Phạm Thị D", "phone": "0901112223"})
    res = client.get("/api/v1/customers", params={"phone": typed})
    assert res.status_code == 200, res.text
    assert len(res.json()) == 1


def test_phone_rong_khong_tra_ve_toan_bo_danh_sach(client: TestClient) -> None:
    """🔴 Chuỗi rỗng KHÔNG được rơi về nhánh "liệt kê tất cả".

    Nếu rơi, thì một ô tìm kiếm bị xoá trắng sẽ **đổ toàn bộ danh sách khách
    hàng** ra màn hình quầy — đúng thứ phép tra theo số điện thoại sinh ra để
    tránh.
    """
    client.post("/api/v1/customers", json={"full_name": "Võ Thị E", "phone": "0933444555"})
    res = client.get("/api/v1/customers", params={"phone": ""})
    assert res.status_code == 200
    assert res.json() == []
