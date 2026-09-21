from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kdmp_api.modules.cooperatives.model import Cooperative
from kdmp_api.modules.cooperatives.schemas import (
    CooperativeCollection,
    CooperativeFeature,
    CooperativeProperties,
    PointGeometry,
)
from kdmp_api.modules.cooperatives.spatial import BoundingBox


def find_in_bbox(session: Session, bbox: BoundingBox, limit: int) -> CooperativeCollection:
    envelope = func.ST_MakeEnvelope(bbox.west, bbox.south, bbox.east, bbox.north, 4326)
    statement = (
        select(
            Cooperative.id,
            Cooperative.name,
            Cooperative.village_code,
            Cooperative.source,
            func.ST_X(Cooperative.location).label("longitude"),
            func.ST_Y(Cooperative.location).label("latitude"),
        )
        .where(func.ST_Intersects(Cooperative.location, envelope))
        .order_by(Cooperative.id)
        .limit(limit + 1)
    )
    rows = session.execute(statement).all()
    features = [
        CooperativeFeature(
            id=row.id,
            geometry=PointGeometry(coordinates=(row.longitude, row.latitude)),
            properties=CooperativeProperties(
                name=row.name, village_code=row.village_code, source=row.source
            ),
        )
        for row in rows[:limit]
    ]
    return CooperativeCollection(
        features=features, numberReturned=len(features), truncated=len(rows) > limit
    )
