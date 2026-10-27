"""Trace draft submissions to their source and flag organizer review decisions."""

import sqlalchemy as sa
from alembic import op

revision = "20261027_roster_review"
down_revision = "20261027_poster_lookup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    columns = {item["name"] for item in sa.inspect(connection).get_columns("Project")}
    for column in (
        sa.Column("Source_Submission_Key", sa.String(128), nullable=True),
        sa.Column("Roster_Review", sa.JSON(), nullable=True),
        sa.Column(
            "Roster_Review_Required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    ):
        if column.name not in columns:
            op.add_column("Project", column)
    indexes = {item["name"] for item in sa.inspect(connection).get_indexes("Project")}
    if "uq_project_source_submission" not in indexes:
        op.create_index(
            "uq_project_source_submission",
            "Project",
            ["Event_ID", "Source_Submission_Key"],
            unique=True,
        )


def downgrade() -> None:
    op.drop_index("uq_project_source_submission", table_name="Project")
    with op.batch_alter_table("Project") as batch:
        for column in (
            "Roster_Review_Required",
            "Roster_Review",
            "Source_Submission_Key",
        ):
            batch.drop_column(column)
