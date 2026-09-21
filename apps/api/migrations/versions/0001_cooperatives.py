"""Create the public cooperative point foundation."""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry

revision = "0001_cooperatives"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Extension is provisioned by the DB administrator; migrator is not a superuser.
    op.execute("SELECT PostGIS_Version()")
    op.create_table(
        "cooperatives",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("village_code", sa.String(20), nullable=True),
        sa.Column("location", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_cooperatives_name_nonempty"),
        sa.CheckConstraint("length(trim(source)) > 0", name="ck_cooperatives_source_nonempty"),
        sa.CheckConstraint(
            "NOT ST_IsEmpty(location) AND ST_X(location) BETWEEN -180 AND 180 "
            "AND ST_Y(location) BETWEEN -90 AND 90",
            name="ck_cooperatives_location_valid",
        ),
    )
    op.create_index(
        "ix_cooperatives_location", "cooperatives", ["location"], postgresql_using="gist"
    )


def downgrade() -> None:
    op.drop_index("ix_cooperatives_location", table_name="cooperatives")
    op.drop_table("cooperatives")
