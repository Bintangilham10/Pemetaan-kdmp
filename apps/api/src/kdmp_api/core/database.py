from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from kdmp_api.core.config import Settings


class Base(DeclarativeBase):
    pass


def build_engine(settings: Settings) -> Engine:
    return create_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_timeout_seconds,
        pool_recycle=1800,
        connect_args={
            "connect_timeout": settings.db_timeout_seconds,
            "options": f"-c statement_timeout={settings.db_timeout_seconds * 1000}",
        },
        hide_parameters=True,
    )


def get_session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session
