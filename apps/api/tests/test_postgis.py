import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path
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
from kdmp_api.import_data import (
    ImportManifest,
    ImportPlan,
    ImportRow,
    VillageReference,
    publish_release,
    validate_release,
)
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
        connection.execute(text("SELECT id FROM import_batches LIMIT 1"))
        connection.rollback()
        with pytest.raises(DBAPIError):
            connection.execute(text("DELETE FROM cooperatives"))
        connection.rollback()
        with pytest.raises(DBAPIError):
            connection.execute(text("CREATE TABLE forbidden_table (id int)"))
        connection.rollback()
    engine.dispose()


def test_import_release_switches_public_view_atomically(
    client: TestClient, session: Session, tmp_path: Path
) -> None:
    def plan(version: str, name: str):
        csv_path = tmp_path / "cooperatives.csv"
        csv_path.write_text(
            f"external_id,name,village_code,longitude,latitude\nitem-1,{name},,106.8,-6.2\n",
            encoding="utf-8",
        )
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "dataset_key": "synthetic-test",
                    "version": version,
                    "source_name": "Synthetic integration source",
                    "source_url": "https://example.org/source",
                    "license": "Test only",
                    "retrieved_at": "2026-09-25T00:00:00+07:00",
                    "approved_by": "Synthetic reviewer",
                    "approved_at": "2026-09-25T01:00:00+07:00",
                    "file_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
                    "expected_rows": 1,
                }
            ),
            encoding="utf-8",
        )
        return validate_release(manifest_path, csv_path)

    first = plan("v1", "First edition")
    first_id = publish_release(session, first)
    viewport = "/api/v1/cooperatives?bbox=106,-7,108,-5"
    assert client.get(viewport).json()["features"][0]["properties"]["name"] == "First edition"
    with pytest.raises(ValueError, match="already imported"):
        publish_release(session, first)

    with pytest.raises(ValueError, match="approval must be newer"):
        publish_release(session, plan("v2", "Second edition"))

    second = plan("v2", "Second edition")
    second.manifest.approved_at = second.manifest.approved_at.replace(day=26)
    second_id = publish_release(session, second)
    features = client.get(viewport).json()["features"]
    assert len(features) == 1
    assert features[0]["properties"]["name"] == "Second edition"
    assert (
        session.execute(
            text("SELECT count(*) FROM cooperatives WHERE import_batch_id IS NOT NULL")
        ).scalar_one()
        == 2
    )
    assert (
        session.execute(
            text("SELECT active FROM import_batches WHERE id=:id"), {"id": first_id}
        ).scalar_one()
        is False
    )
    assert (
        session.execute(
            text("SELECT active FROM import_batches WHERE id=:id"), {"id": second_id}
        ).scalar_one()
        is True
    )

    invalid = ImportPlan(
        second.manifest.model_copy(
            update={"version": "v3", "approved_at": second.manifest.approved_at.replace(day=27)}
        ),
        [second.rows[0], second.rows[0]],
    )
    with pytest.raises(DBAPIError), session.begin_nested():
        publish_release(session, invalid)
    assert client.get(viewport).json()["features"][0]["properties"]["name"] == "Second edition"
    assert session.execute(text("SELECT count(*) FROM import_batches")).scalar_one() == 2


def test_import_persists_village_reference_provenance(session: Session) -> None:
    reference = VillageReference(
        version="2026-test",
        source_url="https://example.org/villages",
        file_sha256="0" * 64,
        expected_codes=1,
    )
    manifest = ImportManifest(
        dataset_key="reference-test",
        version="v1",
        source_name="Reference integration source",
        source_url="https://example.org/source",
        license="Test only",
        retrieved_at="2026-09-25T00:00:00+07:00",
        approved_by="Synthetic reviewer",
        approved_at="2026-09-25T01:00:00+07:00",
        file_sha256="1" * 64,
        expected_rows=1,
        village_reference=reference,
    )
    batch_id = publish_release(
        session,
        ImportPlan(
            manifest,
            [ImportRow("reference-1", "Reference test", "3171010001", 106.8, -6.2)],
        ),
    )
    row = session.execute(
        text(
            "SELECT village_reference_version, village_reference_source_url, "
            "village_reference_sha256 FROM import_batches WHERE id=:id"
        ),
        {"id": batch_id},
    ).one()
    assert row == ("2026-test", "https://example.org/villages", "0" * 64)
