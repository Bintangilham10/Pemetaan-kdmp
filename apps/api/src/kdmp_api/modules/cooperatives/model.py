from datetime import datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry, WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from kdmp_api.core.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint("dataset_key", "version", name="uq_import_batches_version"),
        CheckConstraint(
            "(village_reference_version IS NULL AND village_reference_source_url IS NULL "
            "AND village_reference_sha256 IS NULL) OR "
            "(village_reference_version IS NOT NULL AND village_reference_source_url IS NOT NULL "
            "AND village_reference_sha256 IS NOT NULL)",
            name="ck_import_batches_village_reference_complete",
        ),
        Index(
            "uq_import_batches_active_key",
            "dataset_key",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    dataset_key: Mapped[str] = mapped_column(String(80))
    version: Mapped[str] = mapped_column(String(100))
    source_name: Mapped[str] = mapped_column(String(200))
    source_url: Mapped[str] = mapped_column(String(2048))
    license: Mapped[str] = mapped_column(String(200))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str] = mapped_column(String(200))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    file_sha256: Mapped[str] = mapped_column(String(64))
    row_count: Mapped[int] = mapped_column(Integer)
    village_reference_version: Mapped[str | None] = mapped_column(String(100))
    village_reference_source_url: Mapped[str | None] = mapped_column(String(2048))
    village_reference_sha256: Mapped[str | None] = mapped_column(String(64))
    active: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


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
        Index("ix_cooperatives_import_batch_id", "import_batch_id"),
        UniqueConstraint("import_batch_id", "external_id", name="uq_cooperatives_import_external"),
        CheckConstraint(
            "(import_batch_id IS NULL) = (external_id IS NULL)",
            name="ck_cooperatives_import_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200))
    village_code: Mapped[str | None] = mapped_column(String(20))
    import_batch_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("import_batches.id", name="fk_cooperatives_import_batch_id")
    )
    external_id: Mapped[str | None] = mapped_column(String(120))
    location: Mapped[WKBElement] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    source: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
