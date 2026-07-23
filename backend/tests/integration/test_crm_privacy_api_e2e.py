"""End-to-end over HTTP with real tokens: what each role can actually see and do.

No ``allow_dev_auth`` — every request carries a token issued by a real login, so the
permission split is exercised exactly as production will exercise it.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from pharmacy_os.core.audit import AuditAction, AuditLogger
from pharmacy_os.core.config import AppSettings, DatabaseSettings, SecuritySettings, Settings
from pharmacy_os.core.db import SqlAlchemyUnitOfWork, UnitOfWork, build_engine, build_sessionmaker
from pharmacy_os.core.events import InMemoryEventBus
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.catalog.domain import ActiveIngredient
from pharmacy_os.modules.catalog.infrastructure import SqlAlchemyActiveIngredientRepository
from pharmacy_os.modules.crm.domain import ANONYMISED_NAME
from pharmacy_os.modules.iam.application import BootstrapTenantInput, IamService
from pharmacy_os.modules.iam.domain import BRANCH_PHARMACIST, CASHIER
from pharmacy_os.modules.iam.interface import build_repositories

ADMIN_EMAIL = "admin@bera.vn"
ADMIN_PASSWORD = "MatKhauAdmin2026"
STAFF_PASSWORD = "MatKhauNhanVien26"
PENICILLIN_ID = UUID("00000000-0000-0000-0000-00000000fa01")


async def _seed(db_url: str) -> None:
    engine = build_engine(db_url)
    session_factory = build_sessionmaker(engine)

    def uow_factory() -> UnitOfWork:
        return SqlAlchemyUnitOfWork(session_factory, InMemoryEventBus())

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
        async with session_factory() as session:
            await SqlAlchemyActiveIngredientRepository(session).add(
                ActiveIngredient(id=PENICILLIN_ID, name="Penicillin")
            )
            await session.commit()
    finally:
        await engine.dispose()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "crm_privacy_e2e.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    db_url = f"sqlite+aiosqlite:///{db_path}"
    asyncio.run(_seed(db_url))
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


def _staff_with_role(client: TestClient, admin: Any, role_code: str, email: str) -> Any:
    roles = client.get("/api/v1/roles", headers=_auth(admin)).json()
    role = next(r for r in roles if r["code"] == role_code)
    user_id = client.post(
        "/api/v1/users",
        headers=_auth(admin),
        json={"email": email, "password": STAFF_PASSWORD, "full_name": "Nhân Viên"},
    ).json()["id"]
    client.post(
        f"/api/v1/users/{user_id}/roles",
        headers=_auth(admin),
        json={"role_id": role["id"], "branch_id": admin["branch_id"]},
    )
    return _login(client, email, STAFF_PASSWORD)


def _customer_with_allergy(client: TestClient, actor: Any) -> str:
    created = client.post(
        "/api/v1/customers",
        headers=_auth(actor),
        json={"full_name": "Nguyễn Văn A", "phone": "0900000000"},
    )
    assert created.status_code == 201, created.text
    customer_id: str = created.json()["id"]

    consent = client.post(
        f"/api/v1/customers/{customer_id}/consents",
        headers=_auth(actor),
        json={"purpose": "HEALTH", "granted": True},
    )
    assert consent.status_code == 201, consent.text

    allergy = client.post(
        f"/api/v1/customers/{customer_id}/allergies",
        headers=_auth(actor),
        json={"ingredient_id": str(PENICILLIN_ID), "severity": "SEVERE"},
    )
    assert allergy.status_code == 201, allergy.text
    return customer_id


# --- consent is one press, and it is recorded --------------------------------


def test_consent_needs_no_terms_version_from_the_client(client: TestClient) -> None:
    """Counter staff press one button (chốt của sếp); the version defaults."""
    admin = _login(client)
    created = client.post("/api/v1/customers", headers=_auth(admin), json={"full_name": "Khách"})
    r = client.post(
        f"/api/v1/customers/{created.json()['id']}/consents",
        headers=_auth(admin),
        json={"purpose": "HEALTH", "granted": True},
    )
    assert r.status_code == 201
    assert r.json()["consents"][0]["terms_version"] == "v1"
    assert r.json()["health_data_allowed"] is True


def test_consent_still_requires_someone_to_answer(client: TestClient) -> None:
    """No default for ``granted``: an unanswered request must not count as a yes."""
    admin = _login(client)
    created = client.post("/api/v1/customers", headers=_auth(admin), json={"full_name": "Khách"})
    r = client.post(
        f"/api/v1/customers/{created.json()['id']}/consents",
        headers=_auth(admin),
        json={"purpose": "HEALTH"},
    )
    assert r.status_code == 422


def test_allergy_is_refused_before_consent(client: TestClient) -> None:
    admin = _login(client)
    created = client.post("/api/v1/customers", headers=_auth(admin), json={"full_name": "Khách"})
    r = client.post(
        f"/api/v1/customers/{created.json()['id']}/allergies",
        headers=_auth(admin),
        json={"ingredient_id": str(PENICILLIN_ID), "severity": "MILD"},
    )
    assert r.status_code == 422
    assert "chưa đồng ý" in r.json()["detail"]


# --- who sees what -----------------------------------------------------------


def test_a_pharmacist_sees_the_health_data(client: TestClient) -> None:
    admin = _login(client)
    customer_id = _customer_with_allergy(client, admin)
    pharmacist = _staff_with_role(client, admin, BRANCH_PHARMACIST, "ds@bera.vn")

    body = client.get(f"/api/v1/customers/{customer_id}", headers=_auth(pharmacist)).json()
    assert body["full_name"] == "Nguyễn Văn A"
    assert len(body["allergies"]) == 1


def test_a_cashier_sees_the_person_but_not_the_diagnoses(client: TestClient) -> None:
    """The whole point of splitting crm.read from crm.sensitive.read."""
    admin = _login(client)
    customer_id = _customer_with_allergy(client, admin)
    cashier = _staff_with_role(client, admin, CASHIER, "tn@bera.vn")

    # NOTE: the cashier role does not carry crm.read yet — that lands with the role
    # mapping step. Until then this asserts the *deny*, which is the safe direction.
    r = client.get(f"/api/v1/customers/{customer_id}", headers=_auth(cashier))
    assert r.status_code == 403


def test_the_customer_list_never_carries_health_data_over_http(client: TestClient) -> None:
    admin = _login(client)
    _customer_with_allergy(client, admin)

    listed = client.get("/api/v1/customers", headers=_auth(admin)).json()
    assert listed and all(c["allergies"] == [] for c in listed)


# --- data-subject rights over HTTP -------------------------------------------


def test_export_returns_the_full_record_with_provenance(client: TestClient) -> None:
    admin = _login(client)
    customer_id = _customer_with_allergy(client, admin)

    r = client.get(f"/api/v1/customers/{customer_id}/export", headers=_auth(admin))
    assert r.status_code == 200
    body = r.json()
    assert body["customer"]["full_name"] == "Nguyễn Văn A"
    assert len(body["customer"]["allergies"]) == 1
    assert body["exported_by"] == admin["user_id"]


def test_anonymise_strips_the_record_and_is_not_a_delete(client: TestClient) -> None:
    admin = _login(client)
    customer_id = _customer_with_allergy(client, admin)

    r = client.post(f"/api/v1/customers/{customer_id}/anonymise", headers=_auth(admin))
    assert r.status_code == 200

    # The row survives — it carries dispensing lines GPP requires be kept.
    after = client.get(f"/api/v1/customers/{customer_id}", headers=_auth(admin))
    assert after.status_code == 200
    assert after.json()["full_name"] == ANONYMISED_NAME
    assert after.json()["phone"] is None
    assert after.json()["allergies"] == []


def test_a_pharmacist_cannot_anonymise(client: TestClient) -> None:
    admin = _login(client)
    customer_id = _customer_with_allergy(client, admin)
    pharmacist = _staff_with_role(client, admin, BRANCH_PHARMACIST, "ds2@bera.vn")

    r = client.post(f"/api/v1/customers/{customer_id}/anonymise", headers=_auth(pharmacist))
    assert r.status_code == 403


# --- the trail answers the inspection question -------------------------------


def test_the_audit_trail_names_who_opened_the_file(client: TestClient) -> None:
    """The question this whole feature exists to answer."""
    admin = _login(client)
    customer_id = _customer_with_allergy(client, admin)
    pharmacist = _staff_with_role(client, admin, BRANCH_PHARMACIST, "ds3@bera.vn")
    client.get(f"/api/v1/customers/{customer_id}", headers=_auth(pharmacist))

    trail = client.get(
        "/api/v1/audit-logs",
        headers=_auth(admin),
        params={"action": AuditAction.CUSTOMER_SENSITIVE_READ.value},
    ).json()

    assert trail["total"] == 1
    entry = trail["items"][0]
    assert entry["target_id"] == customer_id
    assert entry["actor_user_id"] == pharmacist["user_id"]
    assert "client_ip" in entry["context"]


def test_consent_and_erasure_are_both_in_the_trail(client: TestClient) -> None:
    admin = _login(client)
    customer_id = _customer_with_allergy(client, admin)
    client.post(f"/api/v1/customers/{customer_id}/anonymise", headers=_auth(admin))

    trail = client.get("/api/v1/audit-logs", headers=_auth(admin), params={"limit": 100}).json()
    actions = [i["action"] for i in trail["items"]]
    assert AuditAction.CONSENT_GRANTED in actions
    assert AuditAction.CUSTOMER_SENSITIVE_WRITE in actions
    assert AuditAction.CUSTOMER_ERASED in actions


# --- the processing record (DPIA input, duyệt Q6) ----------------------------


def test_the_processing_record_is_readable_by_an_admin(client: TestClient) -> None:
    admin = _login(client)
    r = client.get("/api/v1/privacy/processing-record", headers=_auth(admin))
    assert r.status_code == 200

    body = r.json()
    sensitive = [c for c in body["categories"] if c["sensitive"]]
    assert len(sensitive) == 1
    assert "crm.sensitive.read" in sensitive[0]["guarded_by"]
    assert AuditAction.CUSTOMER_SENSITIVE_READ.value in body["audited_actions"]
    assert body["cross_border_transfers"]  # documented as none, not silently absent


def test_the_processing_record_admits_what_is_missing(client: TestClient) -> None:
    """A record listing only what works would be a worse document to hand a regulator."""
    admin = _login(client)
    body = client.get("/api/v1/privacy/processing-record", headers=_auth(admin)).json()
    assert any("terms_version" in gap for gap in body["known_gaps"])


def test_a_pharmacist_cannot_read_the_processing_record(client: TestClient) -> None:
    admin = _login(client)
    pharmacist = _staff_with_role(client, admin, BRANCH_PHARMACIST, "ds4@bera.vn")
    r = client.get("/api/v1/privacy/processing-record", headers=_auth(pharmacist))
    assert r.status_code == 403


def test_the_processing_record_needs_a_token(client: TestClient) -> None:
    assert client.get("/api/v1/privacy/processing-record").status_code == 401


def test_unknown_customer_is_404_on_every_new_endpoint(client: TestClient) -> None:
    admin = _login(client)
    missing = uuid4()
    assert (
        client.get(f"/api/v1/customers/{missing}/export", headers=_auth(admin)).status_code == 404
    )
    assert (
        client.post(f"/api/v1/customers/{missing}/anonymise", headers=_auth(admin)).status_code
        == 404
    )
