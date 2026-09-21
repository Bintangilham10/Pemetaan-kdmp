from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from kdmp_api.core.database import Base


class Cooperative(Base):
    __tablename__ = "cooperatives"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="ck_cooperatives_name_nonempty"),
        CheckConstraint("length(trim(source)) > 0", name="ck_cooperatives_source_nonempty"),
        CheckConstraint(
            "NOT ST_IsEmpty(location) AND ST_X(location) BETWEEN -180 AND 180 "
            "AND ST_Y(location) BETWEEN -90 AND 90",
            name="ck_cooperatives_location_valid",
        ),
        Index("ix_cooperatives_location", "location", postgresql_using="gist"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    village_code: Mapped[str | None] = mapped_column(String(20))
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    source: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
