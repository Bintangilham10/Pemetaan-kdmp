"""Track immutable source releases and publish only the active release."""

import sqlalchemy as sa
from alembic import op

revision = "0002_import_batches"
down_revision = "0001_cooperatives"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("dataset_key", sa.String(80), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("license", sa.String(200), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.String(200), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_key", "version", name="uq_import_batches_version"),
    )
    op.create_index(
        "uq_import_batches_active_key",
        "import_batches",
        ["dataset_key"],
        unique=True,
        postgresql_where=sa.text("active"),
    )
    op.add_column("cooperatives", sa.Column("import_batch_id", sa.Uuid(), nullable=True))
    op.add_column("cooperatives", sa.Column("external_id", sa.String(120), nullable=True))
    op.create_foreign_key(
        "fk_cooperatives_import_batch_id",
        "cooperatives",
        "import_batches",
        ["import_batch_id"],
        ["id"],
    )
    op.create_check_constraint(
        "ck_cooperatives_import_identity",
        "cooperatives",
        "(import_batch_id IS NULL) = (external_id IS NULL)",
    )
    op.create_unique_constraint(
        "uq_cooperatives_import_external", "cooperatives", ["import_batch_id", "external_id"]
    )
    op.create_index("ix_cooperatives_import_batch_id", "cooperatives", ["import_batch_id"])


def downgrade() -> None:
    op.drop_index("ix_cooperatives_import_batch_id", table_name="cooperatives")
    op.drop_constraint("uq_cooperatives_import_external", "cooperatives", type_="unique")
    op.drop_constraint("ck_cooperatives_import_identity", "cooperatives", type_="check")
    op.drop_constraint("fk_cooperatives_import_batch_id", "cooperatives", type_="foreignkey")
    op.drop_column("cooperatives", "external_id")
    op.drop_column("cooperatives", "import_batch_id")
    op.drop_index("uq_import_batches_active_key", table_name="import_batches")
    op.drop_table("import_batches")
