import os
from collections.abc import Iterator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from kdmp_api.core.config import Settings
from kdmp_api.core.database import get_session
from kdmp_api.main import create_app

pytestmark = pytest.mark.integration


@pytest.fixture
def session() -> Iterator[Session]:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail("TEST_DATABASE_URL required: run the isolated compose.test.yaml stack")
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Integration fixtures require a dedicated database ending in _test")
    engine = create_engine(url, hide_parameters=True)
    with engine.connect() as connection, connection.begin() as transaction:
        with Session(connection, join_transaction_mode="create_savepoint") as db_session:
            yield db_session
        transaction.rollback()
    engine.dispose()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    settings = Settings(environment="test", database_url=SecretStr(os.environ["TEST_DATABASE_URL"]))
    app = create_app(settings)
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client


def insert_point(session: Session, index: int, lon: float, lat: float) -> None:
    session.execute(
        text(
            "INSERT INTO cooperatives (id, name, location, source) "
            "VALUES (:id, :name, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), "
            "'integration-test-only')"
        ),
        {"id": UUID(int=index), "name": f"Synthetic test {index}", "lon": lon, "lat": lat},
    )


def test_ready_checks_postgis_and_migration(client: TestClient) -> None:
    assert client.get("/health/ready").json() == {
        "status": "ok",
        "database": "ok",
        "spatial": "ok",
        "schema": "ok",
    }


def test_ready_rejects_wrong_schema_revision(client: TestClient, session: Session) -> None:
    session.execute(text("UPDATE alembic_version SET version_num='wrong_revision'"))
    assert client.get("/health/ready").status_code == 503


def test_spatial_filter_order_limit_and_geojson(client: TestClient, session: Session) -> None:
    insert_point(session, 1, 110, -7)
    insert_point(session, 2, 111, -7)
    insert_point(session, 3, 120, 0)
    response = client.get("/api/v1/cooperatives?bbox=109,-8,112,-6&limit=1")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert data["numberReturned"] == 1
    assert data["truncated"] is True
    assert data["features"][0]["geometry"]["coordinates"] == [110, -7]
    assert data["features"][0]["id"] == str(UUID(int=1))
    all_data = client.get("/api/v1/cooperatives?bbox=109,-8,112,-6&limit=10").json()
    assert all_data["numberReturned"] == 2
    assert all_data["truncated"] is False
    assert client.get("/api/v1/cooperatives?bbox=90,0,91,1").json()["features"] == []


def test_bbox_includes_boundary_point(client: TestClient, session: Session) -> None:
    insert_point(session, 1, 110, -7)
    assert client.get("/api/v1/cooperatives?bbox=110,-7,111,-6").json()["numberReturned"] == 1


def test_database_rejects_invalid_coordinates(session: Session) -> None:
    with pytest.raises(DBAPIError), session.begin_nested():
        insert_point(session, 1, 181, -7)


def test_gist_index_exists(session: Session) -> None:
    definition = session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE indexname='ix_cooperatives_location'")
    ).scalar_one()
    assert "USING gist (location)" in definition


def test_runtime_role_is_readonly() -> None:
    url = os.environ["TEST_READONLY_DATABASE_URL"]
    if not (make_url(url).database or "").endswith("_test"):
        pytest.fail("Read-only role test requires an isolated _test database")
    engine = create_engine(url, hide_parameters=True)
    with engine.connect() as connection:
        assert (
            connection.execute(
                text("SELECT rolsuper FROM pg_roles WHERE rolname=current_user")
            ).scalar_one()
            is False
        )
        connection.execute(text("SELECT id FROM cooperatives LIMIT 1"))
        connection.rollback()
        with pytest.raises(DBAPIError):
            connection.execute(text("DELETE FROM cooperatives"))
        connection.rollback()
        with pytest.raises(DBAPIError):
            connection.execute(text("CREATE TABLE forbidden_table (id int)"))
        connection.rollback()
    engine.dispose()
