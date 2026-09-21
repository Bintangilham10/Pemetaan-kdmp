from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from kdmp_api.core.config import Settings
from kdmp_api.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        database_url=SecretStr("postgresql+psycopg://test@localhost/kdmp_test"),
        allowed_hosts=["testserver", "localhost"],
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
