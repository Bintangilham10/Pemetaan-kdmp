"""Record the versioned village reference used for each imported release."""

import sqlalchemy as sa
from alembic import op

revision = "0003_village_reference"
down_revision = "0002_import_batches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("import_batches", sa.Column("village_reference_version", sa.String(100)))
    op.add_column("import_batches", sa.Column("village_reference_source_url", sa.String(2048)))
    op.add_column("import_batches", sa.Column("village_reference_sha256", sa.String(64)))
    op.create_check_constraint(
        "ck_import_batches_village_reference_complete",
        "import_batches",
        "(village_reference_version IS NULL AND village_reference_source_url IS NULL "
        "AND village_reference_sha256 IS NULL) OR "
        "(village_reference_version IS NOT NULL AND village_reference_source_url IS NOT NULL "
        "AND village_reference_sha256 IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_import_batches_village_reference_complete", "import_batches", type_="check"
    )
    op.drop_column("import_batches", "village_reference_sha256")
    op.drop_column("import_batches", "village_reference_source_url")
    op.drop_column("import_batches", "village_reference_version")
