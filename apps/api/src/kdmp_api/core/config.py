from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KDMP_", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "api", "testserver"]
    cors_origins: list[str] = []
    db_pool_size: int = Field(default=5, ge=1, le=50)
    db_max_overflow: int = Field(default=5, ge=0, le=50)
    db_timeout_seconds: int = Field(default=5, ge=1, le=30)

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("Use a postgresql+psycopg database URL")
        return value

    @field_validator("allowed_hosts", "cors_origins")
    @classmethod
    def forbid_wildcards(cls, values: list[str]) -> list[str]:
        if any("*" in value for value in values):
            raise ValueError("Explicit hosts and origins are required")
        return values


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
