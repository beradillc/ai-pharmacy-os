"""Ảnh đơn thuốc ETC — gắn, xem, phân quyền, ghi vết. Qua HTTP thật.

Vì sao qua HTTP: cổng thật của tính năng này là **phân quyền** (`rx.image.read` tách khỏi
`rx.read`) và **ghi vết phép đọc**. Cả hai chỉ sống ở tầng service + router đã nối dây; một
test tầng domain không phân biệt được thu ngân với dược sĩ.

🔴 Ảnh đơn thuốc là dữ liệu cá nhân **nhạy cảm** (Luật 91/2025): tên, tuổi, chẩn đoán, tên
bác sĩ. Khác mọi PII đã xử lý trước nay, nó **không cắt nhỏ được** — không có cách nào che
riêng phần chẩn đoán như đã che số điện thoại (ADR-0002). Nên hai phép kiểm quan trọng nhất
ở tệp này là: **thu ngân KHÔNG xem được**, và **mỗi lượt xem đều để lại dấu**.
"""

from __future__ import annotations

import base64
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

#: Một JPEG bé xíu nhưng THẬT — hai byte đầu `\xff\xd8` là chữ ký JPEG. Dùng chuỗi rác
#: base64 sẽ đi qua mọi phép kiểm ở đây mà không chứng minh được gì về ảnh thật.
_JPEG = base64.b64encode(bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")).decode()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "rx_image.db"
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
        json={"name": f"Thuốc-{uuid4().hex[:6]}", "rx_class": "ETC", "base_unit": "viên"},
    )
    assert r.status_code == 201, r.text
    drug_id: str = r.json()["id"]
    return drug_id


def _customer(client: TestClient) -> str:
    r = client.post("/api/v1/customers", json={"full_name": "Khách Thử", "phone": None})
    assert r.status_code == 201, r.text
    customer_id: str = r.json()["id"]
    return customer_id


def _rx(client: TestClient) -> str:
    r = client.post(
        "/api/v1/prescriptions",
        json={
            "customer_id": _customer(client),
            "doctor_name": "BS. Thử",
            "items": [
                {
                    "drug_id": _drug(client),
                    "quantity": "10",
                    "dose": "1 viên",
                    "frequency": "2 lần/ngày",
                    "duration": "5 ngày",
                }
            ],
        },
    )
    assert r.status_code == 201, r.text
    rx_id: str = r.json()["id"]
    return rx_id


def _attach(client: TestClient, rx_id: str, *, data: str = _JPEG, ct: str = "image/jpeg") -> Any:
    return client.put(
        f"/api/v1/prescriptions/{rx_id}/image",
        json={"image_data": data, "content_type": ct},
    )


def test_gan_anh_roi_xem_lai_duoc_dung_nguyen_ban(client: TestClient) -> None:
    """Ảnh đi qua mã hoá at-rest rồi quay ra phải **giống hệt** — không rơi byte nào."""
    rx_id = _rx(client)
    assert _attach(client, rx_id).status_code == 200

    r = client.get(f"/api/v1/prescriptions/{rx_id}/image")
    assert r.status_code == 200, r.text
    assert r.json()["image_data"] == _JPEG
    assert r.json()["content_type"] == "image/jpeg"


def test_don_chua_co_anh_thi_has_image_la_false(client: TestClient) -> None:
    rx_id = _rx(client)
    r = client.get(f"/api/v1/prescriptions/{rx_id}")
    assert r.status_code == 200, r.text
    assert r.json()["has_image"] is False


def test_gan_anh_xong_has_image_thanh_true_nhung_KHONG_kem_noi_dung(client: TestClient) -> None:
    """🔴 Phép đọc đơn thường **không được** kéo theo ảnh.

    Gộp vào thì mọi lượt xem đơn đều mang dữ liệu nhạy cảm, và dòng audit "ai đã xem ảnh"
    mất hết nghĩa — ai mở đơn cũng thành người đã xem ảnh.
    """
    rx_id = _rx(client)
    _attach(client, rx_id)

    body = client.get(f"/api/v1/prescriptions/{rx_id}").json()
    assert body["has_image"] is True
    assert "image_data" not in body


def test_chup_lai_ghi_de_anh_cu(client: TestClient) -> None:
    """Chụp trượt nét, ngược sáng, thiếu góc là chuyện thường ngày ở quầy."""
    rx_id = _rx(client)
    _attach(client, rx_id)
    khac = base64.b64encode(
        bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9ff")
    ).decode()
    assert _attach(client, rx_id, data=khac).status_code == 200

    assert client.get(f"/api/v1/prescriptions/{rx_id}/image").json()["image_data"] == khac


def test_dinh_dang_khong_nhan_bi_tu_choi(client: TestClient) -> None:
    rx_id = _rx(client)
    assert _attach(client, rx_id, ct="application/pdf").status_code == 422


def test_base64_hong_bi_tu_choi(client: TestClient) -> None:
    """`validate=True` — không có nó, base64 im lặng bỏ qua ký tự lạ và nuốt một ảnh hỏng."""
    rx_id = _rx(client)
    assert _attach(client, rx_id, data="khong-phai-base64!!!").status_code == 422


def test_anh_qua_2MB_bi_tu_choi(client: TestClient) -> None:
    """Trần kích thước là CỔNG, không phải sự tiện lợi: nó canh `pg_dump` khỏi phình."""
    rx_id = _rx(client)
    qua_to = base64.b64encode(b"\xff\xd8" + b"x" * (2 * 1024 * 1024)).decode()
    assert _attach(client, rx_id, data=qua_to).status_code == 422


def test_don_khong_ton_tai_tra_404(client: TestClient) -> None:
    assert _attach(client, str(uuid4())).status_code == 404


def test_don_co_that_nhung_chua_co_anh_tra_404(client: TestClient) -> None:
    rx_id = _rx(client)
    assert client.get(f"/api/v1/prescriptions/{rx_id}/image").status_code == 404


# ─── Đơn tạo TỪ ẢNH: nới liều/tần suất/thời gian, KHÔNG nới gì khác ──────────────


def _tao_don(client: TestClient, *, source: str, dose: str = "1 viên") -> Any:
    return client.post(
        "/api/v1/prescriptions",
        json={
            "customer_id": _customer(client),
            "doctor_name": "BS. Thử",
            "source": source,
            "items": [
                {
                    "drug_id": _drug(client),
                    "quantity": "10",
                    "dose": dose,
                    "frequency": dose,
                    "duration": dose,
                }
            ],
        },
    )


def test_don_tu_ANH_cho_phep_lieu_luong_de_TRONG(client: TestClient) -> None:
    """Người chụp tờ đơn không biết liều — nó chỉ có trên giấy.

    Rỗng ở đây đọc là *"chưa phiên từ ảnh"*, không phải "không có liều". Bắt gõ vào là bắt
    chép tay lại chính tờ vừa chụp; tự điền hộ là bịa dữ liệu lâm sàng.
    """
    assert _tao_don(client, source="IMAGE", dose="").status_code == 201


def test_don_nhap_TAY_van_phai_co_du_lieu_luong(client: TestClient) -> None:
    """🔴 Nới cho ảnh KHÔNG được nới cho đường nhập tay — đó là hai việc khác nhau."""
    assert _tao_don(client, source="MANUAL", dose="").status_code == 422


def test_don_nhap_tay_co_du_lieu_luong_van_tao_duoc(client: TestClient) -> None:
    assert _tao_don(client, source="MANUAL").status_code == 201


def test_don_tu_anh_VAN_phai_co_it_nhat_mot_dong_thuoc(client: TestClient) -> None:
    """🔴 Không nới `items`, kể cả cho ảnh.

    Đơn rỗng dòng sẽ **kẹt vĩnh viễn ở DRAFT**: `validate()` ném `EmptyPrescriptionError`,
    mà module này không có đường thêm dòng sau khi tạo — phải viết endpoint mới để gỡ.
    """
    r = client.post(
        "/api/v1/prescriptions",
        json={
            "customer_id": _customer(client),
            "doctor_name": "BS. Thử",
            "source": "IMAGE",
            "items": [],
        },
    )
    assert r.status_code == 422, r.text


def test_don_tu_anh_de_trong_lieu_VAN_duyet_duoc(client: TestClient) -> None:
    """Bằng chứng cho lập luận ở trên: đơn từ ảnh không phải ngõ cụt."""
    rx_id = _tao_don(client, source="IMAGE", dose="").json()["id"]
    r = client.post(f"/api/v1/prescriptions/{rx_id}/validate")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "VALIDATED"


# ─── Khách không để lại số điện thoại (Chain chốt 2026-07-31, lượt hai) ──────────


def _don_tu_anh(client: TestClient, *, co_khach: bool, source: str = "IMAGE") -> Any:
    body: dict[str, object] = {
        "doctor_name": "BS. Thử",
        "source": source,
        "items": [
            {
                "drug_id": _drug(client),
                "quantity": "10",
                "dose": "" if source == "IMAGE" else "1 viên",
                "frequency": "" if source == "IMAGE" else "2 lần/ngày",
                "duration": "" if source == "IMAGE" else "5 ngày",
            }
        ],
    }
    if co_khach:
        body["customer_id"] = _customer(client)
    return client.post("/api/v1/prescriptions", json=body)


def test_don_tu_ANH_khong_can_khach(client: TestClient) -> None:
    """Chain: *"không cung cấp sdt, chỉ cần chụp đơn thuốc là xong"*.

    Cái mất đã ghi ở `Prescription.customer_id`: không tra lại được theo khách, không xoá
    theo yêu cầu chủ thể được. Chain nghe và quyết ưu tiên việc bán hàng chạy được ở quầy.
    """
    r = _don_tu_anh(client, co_khach=False)
    assert r.status_code == 201, r.text
    assert r.json()["customer_id"] is None


def test_don_nhap_TAY_van_bat_buoc_co_khach(client: TestClient) -> None:
    """🔴 Nới cho ảnh KHÔNG được nới cho đường nhập tay."""
    assert _don_tu_anh(client, co_khach=False, source="MANUAL").status_code == 422


def test_luu_tru_chi_liet_ke_don_DA_CO_ANH(client: TestClient) -> None:
    """Lưu trữ là nơi tra chứng từ — đơn chưa chụp thì không có gì để lưu trữ."""
    _rx(client)  # đơn không ảnh
    co_anh = _rx(client)
    _attach(client, co_anh)

    r = client.get("/api/v1/prescriptions/archive")
    assert r.status_code == 200, r.text
    assert [x["id"] for x in r.json()] == [co_anh]


def test_luu_tru_KHONG_kem_noi_dung_anh(client: TestClient) -> None:
    """Danh sách không mang ảnh — xem ảnh phải hỏi đích danh, và lượt đó mới ghi vết."""
    rx_id = _rx(client)
    _attach(client, rx_id)

    dong = client.get("/api/v1/prescriptions/archive").json()[0]
    assert dong["has_image"] is True
    assert "image_data" not in dong


# ─── Chain điều chỉnh 2026-07-31 (lượt ba): ảnh bất kỳ, biết người chốt đơn ──────


def test_don_tu_ANH_khong_can_TEN_BAC_SI(client: TestClient) -> None:
    """Chain: *"chỉ cần có hình chụp bất kỳ"*.

    Người đứng quầy không phải lúc nào cũng đọc được chữ bác sĩ, và một cái tên đoán mò
    trong hồ sơ trông y hệt một cái tên đã đọc.
    """
    r = client.post(
        "/api/v1/prescriptions",
        json={
            "source": "IMAGE",
            "items": [
                {
                    "drug_id": _drug(client),
                    "quantity": "10",
                    "dose": "",
                    "frequency": "",
                    "duration": "",
                }
            ],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["doctor_name"] == ""


def test_don_nhap_TAY_van_bat_buoc_ten_bac_si(client: TestClient) -> None:
    """🔴 Nới cho ảnh KHÔNG được nới cho đường nhập tay."""
    r = client.post(
        "/api/v1/prescriptions",
        json={
            "customer_id": _customer(client),
            "source": "MANUAL",
            "items": [
                {
                    "drug_id": _drug(client),
                    "quantity": "10",
                    "dose": "1 viên",
                    "frequency": "2 lần/ngày",
                    "duration": "5 ngày",
                }
            ],
        },
    )
    assert r.status_code == 422, r.text


def test_don_ghi_lai_NGUOI_CHOT_DON(client: TestClient) -> None:
    """Chain: *"biết người chốt đơn hàng là trách nhiệm lưu đơn thuốc"*.

    Sổ audit đã ghi từ trước, nhưng phải mở sổ audit mới thấy — và không ai mở sổ audit để
    trả lời một câu hỏi thường ngày. Trách nhiệm chỉ có nghĩa khi nhìn thấy được.
    """
    r = client.post(
        "/api/v1/prescriptions",
        json={
            "source": "IMAGE",
            "items": [
                {
                    "drug_id": _drug(client),
                    "quantity": "1",
                    "dose": "",
                    "frequency": "",
                    "duration": "",
                }
            ],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["created_by"] is not None
