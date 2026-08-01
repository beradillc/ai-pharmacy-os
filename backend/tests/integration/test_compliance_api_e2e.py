"""End-to-end over HTTP: the compliance router mounted for the first time (§7n/§7p).

Confirms the wiring, not the domain rules (those are covered by unit tests in
``tests/unit`` for the ledger/config/sync services) — real token, real DI resolution,
real response shape.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.audit import AuditLogger
from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.iam.application import BootstrapTenantInput, IamService
from pharmacy_os.modules.iam.domain import CASHIER
from pharmacy_os.modules.iam.interface import build_repositories
from tests.conftest import urls_csdl_thu

ADMIN_EMAIL = "admin@bera.vn"
ADMIN_PASSWORD = "MatKhauAdmin2026"
STAFF_PASSWORD = "MatKhauNhanVien26"


async def _bootstrap(db_url: str) -> None:
    engine = build_engine(db_url)
    session_factory = build_sessionmaker(engine)
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
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "compliance_e2e.db"
    _sync_url, _async_url = urls_csdl_thu(db_path)
    sync_engine = create_engine(_sync_url)
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    db_url = _async_url
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


def test_admin_records_and_reads_back_a_controlled_ledger_entry(client: TestClient) -> None:
    admin = _login(client)
    created = client.post(
        "/api/v1/compliance/controlled-ledger",
        headers=_auth(admin),
        json={
            "drug_id": str(uuid4()),
            "category": "HUONG_THAN",
            "direction": "NHAP",
            "quantity": "10",
            "lot_no": "L001",
            "expiry_date": "2027-01-01",
            "transaction_at": "2026-07-23T09:00:00Z",
            "source_or_destination": "Công ty Dược ABC",
            "document_no": "PN-001",
        },
    )
    assert created.status_code == 201, created.text
    entry_id = created.json()["id"]

    fetched = client.get(f"/api/v1/compliance/controlled-ledger/{entry_id}", headers=_auth(admin))
    assert fetched.status_code == 200
    assert fetched.json()["document_no"] == "PN-001"


def test_admin_sets_and_reads_tenant_config(client: TestClient) -> None:
    admin = _login(client)
    r = client.put(
        "/api/v1/compliance/tenant-config",
        headers=_auth(admin),
        json={"ma_co_so_ban_le": "ABC123"},
    )
    assert r.status_code == 200
    assert r.json()["ma_co_so_ban_le"] == "ABC123"

    fetched = client.get("/api/v1/compliance/tenant-config", headers=_auth(admin))
    assert fetched.status_code == 200
    assert fetched.json()["ma_co_so_ban_le"] == "ABC123"


def test_admin_pushes_and_reads_a_sync_log(client: TestClient) -> None:
    admin = _login(client)
    client_uuid = str(uuid4())
    pushed = client.post(
        "/api/v1/compliance/sync-logs",
        headers=_auth(admin),
        json={"payload_type": "sale", "client_uuid": client_uuid, "payload": "{}"},
    )
    assert pushed.status_code == 201, pushed.text
    log_id = pushed.json()["id"]
    assert pushed.json()["status"] == "ACK"  # mock gateway always ACKs

    fetched = client.get(f"/api/v1/compliance/sync-logs/{log_id}", headers=_auth(admin))
    assert fetched.status_code == 200
    assert fetched.json()["client_uuid"] == client_uuid


def test_cashier_cannot_write_the_controlled_ledger(client: TestClient) -> None:
    admin = _login(client)
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    cashier_role = next(r for r in roles if r["code"] == CASHIER)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": "tn@bera.vn", "password": STAFF_PASSWORD, "full_name": "Thu Ngân"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": cashier_role["id"], "branch_id": admin["branch_id"]},
    )
    cashier = _login(client, "tn@bera.vn", STAFF_PASSWORD)

    r = client.post(
        "/api/v1/compliance/controlled-ledger",
        headers=_auth(cashier),
        json={
            "drug_id": str(uuid4()),
            "category": "HUONG_THAN",
            "direction": "NHAP",
            "quantity": "1",
            "lot_no": "L1",
            "expiry_date": "2027-01-01",
            "transaction_at": "2026-07-23T09:00:00Z",
            "source_or_destination": "X",
            "document_no": "D1",
        },
    )
    assert r.status_code == 403


def test_the_ledger_needs_a_token(client: TestClient) -> None:
    assert client.get(f"/api/v1/compliance/controlled-ledger/{uuid4()}").status_code == 401


def _ghi_so(client: TestClient, admin: Any, **overrides: Any) -> str:
    body: dict[str, Any] = {
        "drug_id": str(uuid4()),
        "category": "HUONG_THAN",
        "direction": "NHAP",
        "quantity": "10",
        "lot_no": "L001",
        "expiry_date": "2027-01-01",
        "transaction_at": "2026-07-23T09:00:00Z",
        "source_or_destination": "Công ty Dược ABC",
        "document_no": "PN-001",
    }
    body.update(overrides)
    r = client.post("/api/v1/compliance/controlled-ledger", headers=_auth(admin), json=body)
    assert r.status_code == 201, r.text
    entry_id: str = r.json()["id"]
    return entry_id


def test_ket_xuat_so_phu_luc_viii_ra_csv(client: TestClient) -> None:
    admin = _login(client)
    drug = str(uuid4())
    _ghi_so(client, admin, drug_id=drug, quantity="100")
    _ghi_so(
        client,
        admin,
        drug_id=drug,
        direction="XUAT",
        quantity="30",
        transaction_at="2026-07-24T09:00:00Z",
        prescription_code="RX-1",
        customer={"patient_name": "Nguyễn Văn A", "patient_address": "1 Lê Lợi"},
    )

    r = client.get(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/export",
        headers=_auth(admin),
        params={"date_from": "2026-07-01", "date_to": "2026-07-31", "drug_id": drug},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "so-pl_viii-" in r.headers["content-disposition"]
    dong = [d for d in r.text.splitlines() if d.strip()]
    assert dong[0].startswith("ngay_thang,noi_xuat_nhap,so_chung_tu")
    assert len(dong) == 3  # header + 2 giao dịch
    assert dong[1].split(",")[3:6] == ["100", "", "100"]  # nhập / xuất / còn lại
    assert dong[2].split(",")[3:6] == ["", "30", "70"]


def test_ket_xuat_so_phu_luc_xvi_chi_lay_nhom_dieu_12_3(client: TestClient) -> None:
    """Sổ PL XVI không được lẫn thuốc GN/HT/TC — 2 mẫu sổ là 2 hồ sơ riêng."""
    admin = _login(client)
    thuoc_ht, thuoc_doc = str(uuid4()), str(uuid4())
    _ghi_so(client, admin, drug_id=thuoc_ht, transaction_at="2026-08-03T09:00:00Z")
    _ghi_so(
        client,
        admin,
        drug_id=thuoc_doc,
        category="THUOC_DOC",
        transaction_at="2026-08-03T09:00:00Z",
    )

    r = client.get(
        "/api/v1/compliance/controlled-ledger/books/PL_XVI/export",
        headers=_auth(admin),
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    )
    assert r.status_code == 200, r.text
    noi_dung = r.text
    assert thuoc_doc in noi_dung
    assert thuoc_ht not in noi_dung


def test_ket_xuat_so_can_token(client: TestClient) -> None:
    r = client.get(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/export",
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )
    assert r.status_code == 401


def test_ket_xuat_so_tu_choi_mau_so_khong_ton_tai(client: TestClient) -> None:
    admin = _login(client)
    r = client.get(
        "/api/v1/compliance/controlled-ledger/books/PL_XX/export",
        headers=_auth(admin),
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )
    assert r.status_code == 422


def test_ket_xuat_bao_cao_dinh_ky_mau_so_06(client: TestClient) -> None:
    """NĐ163 Điều 35.2.a — docs/13 mục C.7."""
    admin = _login(client)
    drug = str(uuid4())
    _ghi_so(client, admin, drug_id=drug, direction="NHAP", quantity="80")

    r = client.get(
        "/api/v1/compliance/periodic-report/export",
        headers=_auth(admin),
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "bao-cao-mau06-" in r.headers["content-disposition"]
    dong = [d for d in r.text.splitlines() if d.strip()]
    assert dong[0].startswith("tt,ten_thuoc_day_du,nuoc_san_xuat")
    assert drug in dong[1]
    assert dong[1].split(",")[0] == "1"  # cột TT


def test_ket_xuat_bao_cao_dinh_ky_can_token(client: TestClient) -> None:
    r = client.get(
        "/api/v1/compliance/periodic-report/export",
        params={"date_from": "2026-07-01", "date_to": "2026-07-31"},
    )
    assert r.status_code == 401


def test_ghi_va_doc_bien_ban_nhan_lai_thuoc(client: TestClient) -> None:
    """TT18 Điều 6.2 + Điều 12.1.d, Phụ lục XVIII — docs/13 mục C.6."""
    admin = _login(client)
    body = {
        "returner_name": "Nguyễn Văn A",
        "returner_address": "12 Lê Lợi, Q1, HCM",
        "returner_id_number": "079123456789",
        "returner_id_issuer": "Cục Cảnh sát QLHC về TTXH",
        "returner_id_issued_at": "2021-05-01",
        "returner_is_patient": True,
        "receiving_pharmacist_name": "DS. Trần Thị B",
        "items": [
            {
                "description": "Diazepam 5mg, viên nén, hộp 2 vỉ x 10 viên",
                "unit": "viên",
                "quantity": "3",
                "lot_no": "L20260101",
                "expiry_date": "2028-01-01",
                "condition_note": "Còn nguyên vỉ",
                "reason": "Người bệnh không dùng hết",
            }
        ],
        "handover_at": "2026-07-25T14:30:00Z",
        "handover_location": "Nhà thuốc ABC, 12 Lê Lợi, Q1, HCM",
    }
    created = client.post("/api/v1/compliance/drug-returns", headers=_auth(admin), json=body)
    assert created.status_code == 201, created.text
    record_id = created.json()["id"]
    assert created.json()["returner_id_number"] == "079123456789"

    fetched = client.get(f"/api/v1/compliance/drug-returns/{record_id}", headers=_auth(admin))
    assert fetched.status_code == 200
    assert len(fetched.json()["items"]) == 1
    assert fetched.json()["items"][0]["description"] == "Diazepam 5mg, viên nén, hộp 2 vỉ x 10 viên"


def test_bien_ban_nhan_lai_thuoc_can_it_nhat_1_dong(client: TestClient) -> None:
    admin = _login(client)
    body = {
        "returner_name": "Nguyễn Văn A",
        "returner_address": "12 Lê Lợi",
        "returner_id_number": "079123456789",
        "returner_id_issuer": "Cục Cảnh sát QLHC về TTXH",
        "returner_id_issued_at": "2021-05-01",
        "returner_is_patient": True,
        "receiving_pharmacist_name": "DS. Trần Thị B",
        "items": [],
        "handover_at": "2026-07-25T14:30:00Z",
        "handover_location": "Nhà thuốc ABC",
    }
    r = client.post("/api/v1/compliance/drug-returns", headers=_auth(admin), json=body)
    assert r.status_code == 422


def test_bien_ban_nhan_lai_thuoc_can_token(client: TestClient) -> None:
    r = client.get(f"/api/v1/compliance/drug-returns/{uuid4()}")
    assert r.status_code == 401


def test_ket_xuat_cuoi_ngay_co_hash_toan_ven(client: TestClient) -> None:
    """docs/13 mục C.5 — ghi chú Phụ lục VIII, điều kiện (a) Điều 15.1."""
    admin = _login(client)
    drug = str(uuid4())
    _ghi_so(
        client,
        admin,
        drug_id=drug,
        quantity="10",
        transaction_at="2026-07-25T09:00:00Z",
    )
    _ghi_so(
        client,
        admin,
        drug_id=drug,
        quantity="20",
        transaction_at="2026-07-26T09:00:00Z",
    )

    r = client.get(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/daily-closure",
        headers=_auth(admin),
        params={"day": "2026-07-25"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "cuoi-ngay-" in r.headers["content-disposition"]
    assert len(r.headers["x-content-sha256"]) == 64
    dong = [d for d in r.text.splitlines() if d.strip()]
    assert len(dong) == 2  # header + đúng 1 giao dịch ngày 25/7
    assert dong[1].startswith("2026-07-25,")
    assert dong[1].split(",")[3] == "10"  # số lượng nhập của giao dịch 25/7, không phải 20


def test_ket_xuat_cuoi_ngay_can_token(client: TestClient) -> None:
    r = client.get(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/daily-closure",
        params={"day": "2026-07-25"},
    )
    assert r.status_code == 401


def test_ky_so_dien_tu_thanh_cong_va_moc_xich_hash(client: TestClient) -> None:
    """docs/13 mục C.5, bước 6/6 TT18 — hướng A: re-auth thật qua iam, không mock."""
    admin = _login(client)
    _ghi_so(client, admin, transaction_at="2026-07-24T09:00:00Z")

    first = client.post(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/sign",
        headers=_auth(admin),
        json={"book_date": "2026-07-24", "current_password": ADMIN_PASSWORD},
    )
    assert first.status_code == 201, first.text
    body = first.json()
    assert body["prev_hash"] is None
    assert len(body["content_sha256"]) == 64

    second = client.post(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/sign",
        headers=_auth(admin),
        json={"book_date": "2026-07-25", "current_password": ADMIN_PASSWORD},
    )
    assert second.status_code == 201, second.text
    assert second.json()["prev_hash"] == body["content_sha256"]


def test_ky_so_dien_tu_sai_mat_khau_bi_tu_choi(client: TestClient) -> None:
    admin = _login(client)
    r = client.post(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/sign",
        headers=_auth(admin),
        json={"book_date": "2026-07-25", "current_password": "SaiRoi123456"},
    )
    assert r.status_code == 401, r.text


def test_ky_so_dien_tu_can_token(client: TestClient) -> None:
    r = client.post(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/sign",
        json={"book_date": "2026-07-25", "current_password": ADMIN_PASSWORD},
    )
    assert r.status_code == 401


def test_ky_lai_ngay_da_ky_bi_tu_choi(client: TestClient) -> None:
    admin = _login(client)
    body = {"book_date": "2026-07-25", "current_password": ADMIN_PASSWORD}
    first = client.post(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/sign", headers=_auth(admin), json=body
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/sign", headers=_auth(admin), json=body
    )
    assert second.status_code == 409, second.text


def test_ghi_them_dong_vao_ngay_da_ky_bi_tu_choi(client: TestClient) -> None:
    """docs/13 mục C.5 — hệ quả "ký xong là chốt sổ": không ghi thêm được vào ngày đã ký."""
    admin = _login(client)
    client.post(
        "/api/v1/compliance/controlled-ledger/books/PL_VIII/sign",
        headers=_auth(admin),
        json={"book_date": "2026-07-25", "current_password": ADMIN_PASSWORD},
    )

    r = client.post(
        "/api/v1/compliance/controlled-ledger",
        headers=_auth(admin),
        json={
            "drug_id": str(uuid4()),
            "category": "HUONG_THAN",
            "direction": "NHAP",
            "quantity": "5",
            "lot_no": "L002",
            "expiry_date": "2027-01-01",
            "transaction_at": "2026-07-25T15:00:00Z",
            "source_or_destination": "Công ty Dược ABC",
            "document_no": "PN-002",
        },
    )
    assert r.status_code == 409, r.text
