from fastapi.testclient import TestClient

from pharmacy_os.core.config import (
    AppSettings,
    DatabaseSettings,
    SecuritySettings,
    Settings,
)
from pharmacy_os.main import create_app


def _app_client() -> TestClient:
    settings = Settings(
        app=AppSettings(env="dev", debug=True),
        db=DatabaseSettings(url="sqlite+aiosqlite:///:memory:"),
        security=SecuritySettings(allow_dev_auth=True),
    )
    return TestClient(create_app(settings))


def test_health_ok() -> None:
    with _app_client() as client:
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["service"] == "ai-pharmacy-os"


def test_openapi_served() -> None:
    with _app_client() as client:
        assert client.get("/api/v1/openapi.json").status_code == 200
