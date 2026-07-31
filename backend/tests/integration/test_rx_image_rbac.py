"""🔴 Phép kiểm quan trọng nhất của tính năng ảnh đơn thuốc: **ai KHÔNG được xem**.

Ảnh đơn mang **chẩn đoán** — đúng thứ `crm.sensitive.read` cố ý không cấp cho thu ngân.
Nếu `rx.image.read` không tách khỏi `rx.read`, thu ngân sẽ đọc được bệnh của khách qua
đường ảnh, đi vòng một ranh giới quyền mà Chain đã duyệt. Chain chốt tách (2026-07-31).

Tệp này dùng **JWT thật** (không dev-auth), vì dev-auth cấp toàn quyền nên nó không thể
phân biệt vai — chạy phép kiểm phân quyền dưới dev-auth là một cổng xanh vì lý do sai
(kỷ luật #14).
"""

from __future__ import annotations

import asyncio
import base64
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from pharmacy_os.core.audit import AuditAction, AuditLogger
from pharmacy_os.core.audit.models import AuditLogORM
from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.iam.application import BootstrapTenantInput, IamService
from pharmacy_os.modules.iam.domain import BRANCH_PHARMACIST, CASHIER
from pharmacy_os.modules.iam.interface import build_repositories

ADMIN_EMAIL = "admin@bera.vn"
ADMIN_PASSWORD = "AdminPass@2026"
STAFF_PASSWORD = "StaffPass@2026"

_JPEG = base64.b64encode(bytes.fromhex("ffd8ffe000104a46494600010100000100010000ffd9")).decode()


async def _bootstrap(db_url: str) -> None:
    engine = create_async_engine(db_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    event_bus = InMemoryEventBus()

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, event_bus)

    service = IamService(uow_factory, build_repositories, AuditLogger(session_factory))
    try:
        await service.bootstrap_tenant(
            BootstrapTenantInput(
                tenant_name="Nhà thuốc Bera",
                branch_code="HQ",
                branch_name="Chi nhánh chính",
                admin_email=ADMIN_EMAIL,
                admin_full_name="Nguyễn Quản Trị",
                admin_password=ADMIN_PASSWORD,
            )
        )
    finally:
        await engine.dispose()


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "rx_image_rbac.db"


@pytest.fixture
def client(db_path: Path) -> Iterator[TestClient]:
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    db_url = f"sqlite+aiosqlite:///{db_path}"
    asyncio.run(_bootstrap(db_url))

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=db_url),
        security=SecuritySettings(jwt_secret="test-secret-key-0123456789abcdef"),  # type: ignore[arg-type]
    )
    with TestClient(create_app(settings)) as c:
        yield c


def _login(client: TestClient, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD) -> Any:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(session: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


def _make_staff(client: TestClient, admin: Any, email: str, role_code: str) -> str:
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    role = next(r for r in roles if r["code"] == role_code)
    user_id: str = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": email, "password": STAFF_PASSWORD, "full_name": "Nhân Viên"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": role["id"], "branch_id": admin["branch_id"]},
    )
    return user_id


def _rx_co_anh(client: TestClient, admin: Any) -> str:
    drug = client.post(
        "/api/v1/drugs",
        headers=_auth(admin),
        json={"name": f"Thuốc-{uuid4().hex[:6]}", "rx_class": "ETC", "base_unit": "viên"},
    ).json()["id"]
    customer = client.post(
        "/api/v1/customers", headers=_auth(admin), json={"full_name": "Khách Thử", "phone": None}
    ).json()["id"]
    rx_id: str = client.post(
        "/api/v1/prescriptions",
        headers=_auth(admin),
        json={
            "customer_id": customer,
            "doctor_name": "BS. Thử",
            "items": [
                {
                    "drug_id": drug,
                    "quantity": "10",
                    "dose": "1 viên",
                    "frequency": "2 lần/ngày",
                    "duration": "5 ngày",
                }
            ],
        },
    ).json()["id"]
    r = client.put(
        f"/api/v1/prescriptions/{rx_id}/image",
        headers=_auth(admin),
        json={"image_data": _JPEG, "content_type": "image/jpeg"},
    )
    assert r.status_code == 200, r.text
    return rx_id


def test_thu_ngan_KHONG_xem_duoc_anh_don_thuoc(client: TestClient) -> None:
    """🔴 Ranh giới quyền cả tính năng dựng lên để giữ.

    Thu ngân có `rx.read` — cần biết đơn có hợp lệ để bán hay không. Nhưng ảnh mang chẩn
    đoán, và đó là dữ liệu sức khoẻ.
    """
    admin = _login(client)
    rx_id = _rx_co_anh(client, admin)
    _make_staff(client, admin, "tn@bera.vn", CASHIER)
    thu_ngan = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    # Vẫn đọc được ĐƠN — thu ngân cần biết đơn hợp lệ hay không.
    assert client.get(f"/api/v1/prescriptions/{rx_id}", headers=_auth(thu_ngan)).status_code == 200
    # Nhưng KHÔNG đọc được ẢNH.
    r = client.get(f"/api/v1/prescriptions/{rx_id}/image", headers=_auth(thu_ngan))
    assert r.status_code == 403, r.text


def test_thu_ngan_cung_KHONG_gan_duoc_anh(client: TestClient) -> None:
    """🔴 Kỳ vọng ban đầu của tôi SAI, và cổng phân quyền bắt được — ghi lại vì sao.

    Tôi viết test này với giả định *"chụp và nộp một tờ giấy khác hẳn việc đọc chẩn đoán
    trong đó, nên thu ngân phải gắn được ảnh"*. Chạy lên thì **403**: thu ngân không có
    ``rx.create``.

    Đọc lại `system_roles.py` thì đó **không phải thiếu sót**, mà là ràng buộc pháp lý đã
    ghi từ trước: cấp phát thuốc kê đơn là hành vi Luật Dược Điều 6.5.h dành cho dược sĩ,
    nên thu ngân không có cả ``rx.create``, ``rx.approve`` lẫn ``rx.dispense``. Một thu
    ngân đứng một mình **không bán được đơn ETC**, nên việc họ không gắn được ảnh không
    làm mất đường nào cả.

    ⇒ Nút "Chụp đơn" ở quầy hiện theo ``rx.create``. Sửa kỳ vọng, không nới quyền (kỷ
    luật #17): nới ``rx.create`` cho thu ngân là đổi một ranh giới **pháp lý** để cho một
    test xanh.
    """
    admin = _login(client)
    rx_id = _rx_co_anh(client, admin)
    _make_staff(client, admin, "tn2@bera.vn", CASHIER)
    thu_ngan = _login(client, "tn2@bera.vn", STAFF_PASSWORD)

    r = client.put(
        f"/api/v1/prescriptions/{rx_id}/image",
        headers=_auth(thu_ngan),
        json={"image_data": _JPEG, "content_type": "image/jpeg"},
    )
    assert r.status_code == 403, r.text


def test_moi_luot_XEM_anh_ghi_mot_dong_audit(client: TestClient, db_path: Path) -> None:
    """Che thì không che được — ảnh là một khối. Ghi vết là lớp bảo vệ duy nhất còn lại."""
    admin = _login(client)
    rx_id = _rx_co_anh(client, admin)

    for _ in range(3):
        assert (
            client.get(f"/api/v1/prescriptions/{rx_id}/image", headers=_auth(admin)).status_code
            == 200
        )

    engine = create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        rows = conn.execute(
            select(AuditLogORM).where(
                AuditLogORM.action == AuditAction.RX_IMAGE_VIEWED.value,
                AuditLogORM.target_id == rx_id,
            )
        ).fetchall()
    engine.dispose()
    assert len(rows) == 3  # ba lượt xem, ba dòng — không gộp


# ─── Phạm vi chi nhánh trong Lưu trữ (Chain giao 2026-07-31, lượt hai) ───────────


def _doi_chi_nhanh(db_path: Path, rx_id: str) -> None:
    """Chuyển một đơn sang chi nhánh KHÁC, ghi thẳng CSDL.

    🔴 Vì sao phải làm thủ công: hệ thống **chưa có endpoint tạo chi nhánh**, nên một bộ
    test dựng qua API luôn chỉ có đúng một chi nhánh — và khi đó "lọc theo chi nhánh" với
    "không lọc gì" cho **cùng một kết quả**. Phiên bản đầu của phép kiểm này vì thế đã
    **sống sót một đột biến**: tôi cho `toan_chuoi = True` (ai cũng thấy toàn chuỗi) mà
    24/24 test vẫn xanh. Đúng thứ kỷ luật #14 sinh ra để bắt.
    """
    engine = create_engine(f"sqlite:///{db_path}")
    with engine.begin() as conn:
        kq = conn.execute(
            text("UPDATE prescriptions SET branch_id = :b WHERE id = :i"),
            # 🔴 `.hex` — SQLite lưu UUID **không có dấu gạch**. Truyền dạng có gạch thì
            # `WHERE` khớp 0 dòng và **im lặng**: phiên bản đầu của helper này làm đúng
            # vậy, và phép kiểm đỏ như thể sản phẩm hỏng.
            {"b": uuid4().hex, "i": UUID(rx_id).hex},
        )
        # Đo cả phép đo: một lượt UPDATE không sửa được dòng nào phải làm test đỏ NGAY ở
        # đây, chứ không phải mười dòng sau dưới dạng một khẳng định khó đọc.
        assert kq.rowcount == 1, f"UPDATE khớp {kq.rowcount} dòng, phải là 1"
    engine.dispose()


def test_duoc_si_CHI_NHANH_khong_thay_don_cua_chi_nhanh_khac(
    client: TestClient, db_path: Path
) -> None:
    """🔴 Phép kiểm quan trọng nhất của lượt này, và nó cần HAI chi nhánh mới có nghĩa.

    `archive.read.chain` là quyền **phạm vi**, tách khỏi quyền nội dung `rx.image.read`.
    Dược sĩ chi nhánh có cái thứ hai nhưng không có cái thứ nhất.
    """
    admin = _login(client)
    cua_minh = _rx_co_anh(client, admin)
    cua_chi_nhanh_khac = _rx_co_anh(client, admin)
    _doi_chi_nhanh(db_path, cua_chi_nhanh_khac)

    _make_staff(client, admin, "ds@bera.vn", BRANCH_PHARMACIST)
    ds = _login(client, "ds@bera.vn", STAFF_PASSWORD)

    # Dược sĩ chi nhánh: thấy ĐÚNG đơn của chi nhánh mình, không thấy đơn kia.
    r = client.get("/api/v1/prescriptions/archive", headers=_auth(ds))
    assert r.status_code == 200, r.text
    assert [x["id"] for x in r.json()] == [cua_minh]

    # Chủ chuỗi: thấy CẢ HAI. Không có khẳng định này thì "trả rỗng cho mọi người" cũng
    # qua được cửa.
    r = client.get("/api/v1/prescriptions/archive", headers=_auth(admin))
    assert r.status_code == 200, r.text
    assert {x["id"] for x in r.json()} == {cua_minh, cua_chi_nhanh_khac}


def test_thu_ngan_khong_mo_duoc_luu_tru(client: TestClient) -> None:
    """Lưu trữ hiện ảnh đơn ⇒ cần `rx.image.read`, thứ thu ngân không có."""
    admin = _login(client)
    _rx_co_anh(client, admin)
    _make_staff(client, admin, "tn3@bera.vn", CASHIER)
    thu_ngan = _login(client, "tn3@bera.vn", STAFF_PASSWORD)

    r = client.get("/api/v1/prescriptions/archive", headers=_auth(thu_ngan))
    assert r.status_code == 403, r.text
