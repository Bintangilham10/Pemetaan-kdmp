from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy.exc import OperationalError

from kdmp_api.core.config import Settings
from kdmp_api.core.database import get_session
from kdmp_api.main import create_app
from kdmp_api.modules.cooperatives.spatial import parse_bbox


def test_liveness_has_no_database_dependency(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["cache-control"] == "no-store"
    UUID(response.headers["x-request-id"])


def test_request_id_is_validated(client: TestClient) -> None:
    request_id = str(uuid4())
    assert (
        client.get("/health/live", headers={"X-Request-ID": request_id}).headers["x-request-id"]
        == request_id
    )
    response = client.get("/health/live", headers={"X-Request-ID": "untrusted-value"})
    assert response.headers["x-request-id"] != "untrusted-value"
    UUID(response.headers["x-request-id"])


@pytest.mark.parametrize(
    "value",
    [
        "1,2,3",
        "nan,0,1,2",
        "0,0,inf,2",
        "180,0,181,1",
        "0,-91,1,1",
        "4,0,1,2",
        "0,2,1,2",
        "x,1,2,3",
    ],
)
def test_bbox_rejects_invalid_and_unbounded_input(value: str) -> None:
    with pytest.raises(HTTPException) as exc:
        parse_bbox(value)
    assert exc.value.status_code == 422


def test_bbox_uses_longitude_then_latitude() -> None:
    bbox = parse_bbox("95,-11,141,6")
    assert (bbox.west, bbox.south, bbox.east, bbox.north) == (95, -11, 141, 6)


@pytest.mark.parametrize(
    "query", ["", "?bbox=invalid", "?bbox=95,-11,141,6&limit=0", "?bbox=95,-11,141,6&limit=1001"]
)
def test_api_rejects_unbounded_queries(client: TestClient, query: str) -> None:
    assert client.get(f"/api/v1/cooperatives{query}").status_code == 422


def test_write_endpoints_are_not_exposed(client: TestClient) -> None:
    assert client.post("/api/v1/cooperatives", json={}).status_code == 405


def test_unknown_host_rejected(client: TestClient) -> None:
    assert client.get("/health/live", headers={"Host": "attacker.example"}).status_code == 400


def test_db_errors_are_redacted(client: TestClient) -> None:
    def broken_session():
        raise OperationalError("SECRET_SQL", {}, Exception("SECRET_PASSWORD"))
        yield  # pragma: no cover

    client.app.dependency_overrides[get_session] = broken_session
    response = client.get("/api/v1/cooperatives?bbox=95,-11,141,6")
    assert response.status_code == 503
    assert "SECRET" not in response.text
    assert response.headers["x-request-id"]


def test_production_hides_docs(settings: Settings) -> None:
    settings.environment = "production"
    with TestClient(create_app(settings)) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_settings_require_postgres_and_explicit_origins() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=SecretStr("sqlite:///local.db"))
    with pytest.raises(ValidationError):
        Settings(database_url=SecretStr("postgresql+psycopg://a@localhost/b"), cors_origins=["*"])
