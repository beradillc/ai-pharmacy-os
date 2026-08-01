"""Che số điện thoại khách ở SERVER + đường mở lộ có quyền riêng (Chain chốt 2026-07-31).

🔴 Lý do file này tồn tại và lý do phép che nằm ở tầng DTO chứ không ở giao diện: che ở
giao diện là **trang trí**. Số đầy đủ vẫn nằm trong phản hồi HTTP, mở tab Network là đọc
được — nó không chặn được ai, chỉ làm người viết mã tưởng đã chặn. Vì vậy hầu hết test ở
đây kiểm **thân phản hồi**, không kiểm cái gì hiện trên màn hình.
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
from pharmacy_os.modules.crm.application.dto import mask_phone
from pharmacy_os.modules.iam.domain.system_roles import (
    SYSTEM_ROLES_BY_CODE,
)
from tests.conftest import urls_csdl_thu

SO_THAT = "0357205494"
DA_CHE = "*494"


# --- phép che, thuần ----------------------------------------------------------


@pytest.mark.parametrize(
    ("vao", "ra"),
    [
        ("0357205494", "*494"),
        ("0912333444", "*444"),
        ("+84357205494", "*494"),  # có mã quốc gia thì vẫn chỉ chừa 3 số cuối
        ("494", "*"),  # 🔴 chừa 3 số cuối của chuỗi 3 ký tự là không che gì
        ("94", "*"),
        ("", ""),
        (None, None),
    ],
)
def test_che_so(vao: str | None, ra: str | None) -> None:
    assert mask_phone(vao) == ra


def test_che_KHONG_lo_do_dai_so() -> None:
    """Một dấu sao, không phải một sao mỗi chữ số (Chain chốt 31/07).

    Ngắn gọn hơn trong bảng hẹp, và tình cờ lộ ít hơn: dãy sao dài đúng bằng phần bị che
    sẽ nói luôn số dài bao nhiêu. Hai số khác độ dài phải cho ra chuỗi che dài bằng nhau.
    """
    assert mask_phone(SO_THAT) == "*494"
    assert len(mask_phone("0357205494") or "") == len(mask_phone("+84357205494") or "")


def test_so_da_che_KHONG_chua_chu_so_nao_khac_ba_so_cuoi() -> None:
    """Canh chính điều phải đúng: không rò chữ số nào ngoài phần được phép."""
    che = mask_phone(SO_THAT) or ""
    assert che[:-3] == "*"
    assert not any(c.isdigit() for c in che[:-3])
    assert che[-3:] == SO_THAT[-3:]


# --- phân quyền ---------------------------------------------------------------


def test_chi_CAP_CHUOI_co_quyen_xem_so_day_du() -> None:
    """🔴 Chain nói "chỉ Chủ chuỗi mới xem được toàn bộ" — đây là chỗ câu đó thành mã.

    Nếu gộp vào ``crm.sensitive.read`` thì dược sĩ **chi nhánh** cũng xem được, và câu
    trên thành sai ngay — đó chính là lý do phải là một quyền riêng.
    """
    co = {c for c, r in SYSTEM_ROLES_BY_CODE.items() if "crm.pii.reveal" in r.permissions}
    assert co == {"system_admin", "chain_pharmacist"}
    khong = SYSTEM_ROLES_BY_CODE["branch_pharmacist"]
    assert "crm.pii.reveal" not in khong.permissions
    assert "crm.sensitive.read" in khong.permissions  # vẫn giữ quyền cũ, không bị lấy mất


# --- qua HTTP thật ------------------------------------------------------------


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "phone_mask.db"
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


def _khach(client: TestClient, phone: str = SO_THAT) -> str:
    r = client.post("/api/v1/customers", json={"full_name": "Khách Thử", "phone": phone})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


def test_tao_khach_xong_phan_hoi_DA_CHE(client: TestClient) -> None:
    r = client.post("/api/v1/customers", json={"full_name": "Khách Thử", "phone": SO_THAT})
    assert r.status_code == 201, r.text
    assert r.json()["phone"] == DA_CHE


def test_danh_sach_khach_KHONG_CHUA_so_day_du_trong_than_phan_hoi(client: TestClient) -> None:
    """🔴 Phép kiểm quan trọng nhất cả file: tìm chuỗi số thật trong **toàn bộ** thân
    phản hồi, không chỉ ở trường ``phone``. Che một trường mà để số rò ở trường khác
    thì vẫn là rò."""
    _khach(client)
    r = client.get("/api/v1/customers")
    assert r.status_code == 200, r.text
    assert SO_THAT not in r.text
    assert DA_CHE in r.text


def test_xem_mot_khach_cung_DA_CHE(client: TestClient) -> None:
    cid = _khach(client)
    r = client.get(f"/api/v1/customers/{cid}")
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == DA_CHE
    assert SO_THAT not in r.text


def test_tim_theo_so_dien_thoai_VAN_CHAY_nhung_tra_ve_so_da_che(client: TestClient) -> None:
    """Che chỉ đổi cái ĐỌC RA, không đổi cái tra vào — quầy vẫn tra khách bằng số."""
    _khach(client)
    r = client.get("/api/v1/customers", params={"phone": SO_THAT})
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    assert r.json()[0]["phone"] == DA_CHE


def test_duong_mo_lo_tra_ve_so_DAY_DU(client: TestClient) -> None:
    cid = _khach(client)
    r = client.get(f"/api/v1/customers/{cid}/phone")
    assert r.status_code == 200, r.text
    assert r.json()["phone"] == SO_THAT
    assert r.json()["customer_id"] == cid


def test_khach_khong_co_so_thi_tra_None_khong_no(client: TestClient) -> None:
    r = client.post("/api/v1/customers", json={"full_name": "Không số", "phone": None})
    cid = str(r.json()["id"])
    assert r.json()["phone"] is None
    r2 = client.get(f"/api/v1/customers/{cid}/phone")
    assert r2.status_code == 200, r2.text
    assert r2.json()["phone"] is None


def test_khach_khong_ton_tai_thi_404(client: TestClient) -> None:
    r = client.get(f"/api/v1/customers/{uuid4()}/phone")
    assert r.status_code == 404, r.text
