import math
from dataclasses import dataclass
from typing import Annotated

from fastapi import HTTPException, Query


@dataclass(frozen=True)
class BoundingBox:
    west: float
    south: float
    east: float
    north: float


def parse_bbox(
    bbox: Annotated[
        str,
        Query(
            description="west,south,east,north in EPSG:4326; no antimeridian crossing",
            min_length=7,
            max_length=120,
            examples=["95,-11,141,6"],
        ),
    ],
) -> BoundingBox:
    try:
        west, south, east, north = (float(part) for part in bbox.split(","))
        if not all(math.isfinite(value) for value in (west, south, east, north)):
            raise ValueError
        if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
            raise ValueError
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="bbox must be west,south,east,north with valid, ordered longitude/latitude",
        ) from exc
    return BoundingBox(west, south, east, north)
