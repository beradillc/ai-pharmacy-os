"""End-to-end HTTP test for the clinical module (routing, DI, mock LLM, DB).

Exercises the real FastAPI app over HTTP with the ``MockLLMProvider`` wired in
bootstrap — no real AI API call is made. Verifies the DoD: the response carries the
reference ``source`` per finding and the model ``confidence``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from pharmacy_os.core.config import AppSettings, DatabaseSettings, Settings
from pharmacy_os.main import create_app
from pharmacy_os.models_registry import Base
from pharmacy_os.modules.clinical.domain import DrugInteraction, InteractionSeverity
from pharmacy_os.modules.clinical.infrastructure.mappers import interaction_to_orm


def _seed_interaction(engine: object, **kw: object) -> None:
    with Session(engine) as session:  # type: ignore[arg-type]
        session.add(
            interaction_to_orm(
                DrugInteraction(
                    ingredient_a=str(kw["a"]),
                    ingredient_b=str(kw["b"]),
                    severity=kw["severity"],  # type: ignore[arg-type]
                    mechanism="cơ chế mẫu",
                    management="xử trí mẫu",
                    source="SAMPLE — test",
                )
            )
        )
        session.commit()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    db_path = tmp_path / "clinical_api.db"
    sync_engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(sync_engine)
    _seed_interaction(sync_engine, a="Warfarin", b="Aspirin", severity=InteractionSeverity.MAJOR)
    _seed_interaction(
        sync_engine, a="Ramipril", b="Ibuprofen", severity=InteractionSeverity.MODERATE
    )
    sync_engine.dispose()

    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url=f"sqlite+aiosqlite:///{db_path}"),
    )
    with TestClient(create_app(settings)) as c:
        yield c


def test_check_interactions_returns_findings_with_source_and_confidence(
    client: TestClient,
) -> None:
    resp = client.post(
        "/api/v1/clinical/check-interactions",
        json={
            "ingredients": ["aspirin", "warfarin", "ramipril", "ibuprofen"],
            "context_type": "SALE",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Deterministic engine: two findings, most-serious first, each with a source.
    severities = [f["severity"] for f in body["findings"]]
    assert severities == ["MAJOR", "MODERATE"]
    assert all(f["source"] for f in body["findings"])

    # DoD: recommendation carries source + confidence and the mock (not a real API).
    rec = body["recommendation"]
    assert rec["model"] == "mock-llm"
    assert 0.0 <= rec["confidence"] <= 1.0
    assert rec["sources"] == ["SAMPLE — test"]
    # A MAJOR finding forces pharmacist review regardless of confidence.
    assert rec["requires_review"] is True
    assert rec["accepted_by"] is None
    assert rec["output"]


def test_check_no_findings_still_audits_recommendation(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/clinical/check-interactions",
        json={"ingredients": ["paracetamol"], "context_type": "RX"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["findings"] == []
    assert body["recommendation"]["sources"] == []
    assert body["recommendation"]["model"] == "mock-llm"


def test_check_then_accept_recommendation_roundtrip(client: TestClient) -> None:
    created = client.post(
        "/api/v1/clinical/check-interactions",
        json={"ingredients": ["warfarin", "aspirin"], "context_type": "SALE"},
    ).json()
    rec_id = created["recommendation"]["id"]

    fetched = client.get(f"/api/v1/clinical/recommendations/{rec_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == rec_id

    accepted = client.post(f"/api/v1/clinical/recommendations/{rec_id}/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted_by"] is not None

    # Accepting twice is a conflict (409).
    again = client.post(f"/api/v1/clinical/recommendations/{rec_id}/accept")
    assert again.status_code == 409, again.text
    assert again.headers["content-type"].startswith("application/problem+json")


def test_empty_ingredients_rejected_by_schema(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/clinical/check-interactions",
        json={"ingredients": [], "context_type": "SALE"},
    )
    assert resp.status_code == 422


def test_blank_ingredients_rejected_by_validator(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/clinical/check-interactions",
        json={"ingredients": ["   ", ""], "context_type": "SALE"},
    )
    assert resp.status_code == 422


def test_get_unknown_recommendation_404(client: TestClient) -> None:
    resp = client.get(f"/api/v1/clinical/recommendations/{uuid4()}")
    assert resp.status_code == 404
