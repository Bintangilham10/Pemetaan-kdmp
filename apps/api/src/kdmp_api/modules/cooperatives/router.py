from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from kdmp_api.core.database import get_session
from kdmp_api.modules.cooperatives.repository import find_in_bbox
from kdmp_api.modules.cooperatives.schemas import CooperativeCollection
from kdmp_api.modules.cooperatives.spatial import BoundingBox, parse_bbox

router = APIRouter(prefix="/cooperatives", tags=["cooperatives"])


@router.get("", response_model=CooperativeCollection, operation_id="list_cooperatives")
def list_cooperatives(
    bbox: Annotated[BoundingBox, Depends(parse_bbox)],
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 500,
) -> CooperativeCollection:
    """Return public cooperative points inside a bounded map viewport."""
    return find_in_bbox(session, bbox, limit)
