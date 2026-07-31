"""End-to-end (C.5): a completed sale enqueues a national-DB sync push.

Drives the real composition root — ``create_app`` wires ``wire_compliance_sync`` —
through the sales HTTP endpoint, so ``SaleCompleted`` is published by the sales
unit-of-work (after commit), not hand-published. The C.5 handler then records a
``NationalSyncLog`` via ``NationalSyncService`` (mock gateway → ACK).

Compliance has no HTTP router yet (§7b), so the log is asserted directly against
the SQLite file the app writes to. Scope per design 5a: sync log only — no
``ControlledLedgerEntry`` is written from the event.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "compliance_sync.db"


@pytest.fixture
def client(db_path: Path) -> Iterator[TestClient]:
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


# 🔴 Từ 2026-07-31 `POST /sales` từ chối `drug_id` không có trong danh mục (phương án B,
# PROJECT_STATE §7co). Trước đó các test ở tệp này bán `uuid4()` ngẫu nhiên — chúng khai
# thác đúng sự khoan dung vừa bị bịt. Tạo thuốc THẬT thay vì nới cổng: một test bán mã
# thuốc không thể tồn tại thì phép khẳng định của nó cũng không nói về hệ thống thật.
def _drug(client: TestClient) -> str:
    r = client.post(
        "/api/v1/drugs",
        json={"name": f"Thuốc-{uuid4().hex[:6]}", "rx_class": "OTC", "base_unit": "viên"},
    )
    assert r.status_code == 201, r.text
    drug_id: str = r.json()["id"]
    return drug_id


def _sale_body(client_uuid: str, drug_id: str, qty: str) -> dict[str, object]:
    return {
        "client_uuid": client_uuid,
        "lines": [{"drug_id": drug_id, "quantity": qty, "unit_price": "10000"}],
        "payments": [{"method": "CASH", "amount": "999999"}],
    }


def _sync_rows(db_path: Path, client_uuid: str) -> list[tuple[str, str]]:
    """(payload_type, status) of every national_sync_logs row for a client_uuid."""
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT payload_type, status FROM national_sync_logs WHERE client_uuid = :cu"),
                {"cu": client_uuid},
            )
            return [(row[0], row[1]) for row in result]
    finally:
        engine.dispose()


def test_sale_enqueues_one_acked_sync_log(client: TestClient, db_path: Path) -> None:
    drug = _drug(client)
    resp = client.post("/api/v1/sales", json=_sale_body("pos-c5-e2e", drug, "3"))
    assert resp.status_code == 201, resp.text

    rows = _sync_rows(db_path, "pos-c5-e2e")
    assert rows == [("sale", "ACK")]  # exactly one SALE log, reached ACK via mock gateway


def test_resync_same_client_uuid_does_not_duplicate_sync_log(
    client: TestClient, db_path: Path
) -> None:
    drug = _drug(client)
    body = _sale_body("offline-c5-e2e", drug, "3")

    client.post("/api/v1/sync/sales", json=body)
    client.post("/api/v1/sync/sales", json=body)  # offline re-sync, same client_uuid

    rows = _sync_rows(db_path, "offline-c5-e2e")
    assert rows == [("sale", "ACK")]  # enqueued exactly once, not duplicated
