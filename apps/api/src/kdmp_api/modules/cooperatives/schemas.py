from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PointGeometry(BaseModel):
    type: Literal["Point"] = "Point"
    coordinates: tuple[float, float]


class CooperativeProperties(BaseModel):
    name: str
    village_code: str | None
    source: str


class CooperativeFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    id: UUID
    geometry: PointGeometry
    properties: CooperativeProperties


class CooperativeCollection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[CooperativeFeature]
    numberReturned: int
    truncated: bool
