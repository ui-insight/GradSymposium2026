"""Add judge name confirmation and an organizer conflict-review flag."""

import sqlalchemy as sa
from alembic import op

from app.db.schema import _ensure_runtime_schema_sync

revision = "20261028_judge_profile"
down_revision = "20261028_five_point_rubric"
branch_labels = None
depends_on = None


def upgrade():
    _ensure_runtime_schema_sync(op.get_bind())


def downgrade():
    connection = op.get_bind()
    if connection.scalar(
        sa.text(
            'SELECT count(*) FROM "Judge" WHERE "Name_Confirmed_At" IS NOT NULL '
            'OR "Previous_Name" IS NOT NULL OR "Conflict_Review_Required" = TRUE'
        )
    ):
        raise RuntimeError(
            "Preserve judge confirmations and conflict reviews before downgrade"
        )
    with op.batch_alter_table("Judge") as batch:
        batch.drop_column("Name_Confirmed_At")
        batch.drop_column("Previous_Name")
        batch.drop_column("Conflict_Review_Required")
