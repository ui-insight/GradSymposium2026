"""Support criterion scores through five and event-specific scale meanings."""

import sqlalchemy as sa
from alembic import op

from app.db.schema import _ensure_runtime_schema_sync
from app.db.score_scale import ensure_score_range

revision = "20261028_five_point_rubric"
down_revision = "20261027_competition"
branch_labels = None
depends_on = None


def upgrade():
    _ensure_runtime_schema_sync(op.get_bind())


def downgrade():
    connection = op.get_bind()
    for table, condition in (
        ("Score", '"Score_Value" > 3'),
        ("Rubric_Criterion", '"Max_Score" > 3'),
        ("Score_Override", '"Old_Score_Value" > 3 OR "New_Score_Value" > 3'),
        (
            "Rubric",
            '"Score_Labels" IS NOT NULL AND '
            "CAST(\"Score_Labels\" AS TEXT) NOT IN ('null', '{}')",
        ),
    ):
        if connection.scalar(
            sa.text(f'SELECT count(*) FROM "{table}" WHERE {condition}')
        ):
            raise RuntimeError(
                "Archive five-point rubrics, scores and scale meanings before "
                "downgrading; competition history will not be discarded"
            )
    ensure_score_range(connection, maximum=3)
    with op.batch_alter_table("Rubric") as batch:
        batch.drop_column("Score_Labels")
