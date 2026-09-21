from pathlib import Path
from typing import Annotated, Literal

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from kdmp_api.core.database import get_session

router = APIRouter(prefix="/health", tags=["health"])
API_ROOT = Path(__file__).resolve().parents[4]


class LiveStatus(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyStatus(LiveStatus):
    database: Literal["ok"] = "ok"
    spatial: Literal["ok"] = "ok"
    schema_status: Literal["ok"] = Field(default="ok", alias="schema")


def migration_head() -> str | None:
    config = Config()
    config.set_main_option("script_location", str(API_ROOT / "migrations"))
    return ScriptDirectory.from_config(config).get_current_head()


@router.get("/live", response_model=LiveStatus, operation_id="liveness")
def liveness() -> LiveStatus:
    return LiveStatus()


@router.get("/ready", response_model=ReadyStatus, operation_id="readiness")
def readiness(session: Annotated[Session, Depends(get_session)]) -> ReadyStatus:
    try:
        session.execute(text("SELECT PostGIS_Version()")).scalar_one()
        revisions = session.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        table_exists = session.execute(
            text("SELECT to_regclass('public.cooperatives')")
        ).scalar_one()
        if revisions != [migration_head()] or table_exists is None:
            raise HTTPException(status_code=503, detail="Service not ready")
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Service not ready") from exc
    return ReadyStatus()
