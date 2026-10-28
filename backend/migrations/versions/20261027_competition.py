"""Add organizer-controlled judging and event-scoped attendee ballots."""

import sqlalchemy as sa
from alembic import op

from app.db.base import Base
from app.db.schema import _ensure_runtime_schema_sync

revision = "20261027_competition"
down_revision = "20261027_roster_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    Base.metadata.create_all(connection)
    _ensure_runtime_schema_sync(connection)


def downgrade() -> None:
    connection = op.get_bind()
    # Never silently discard votes, rules, or explicit eligibility decisions.
    if connection.scalar(
        sa.text(
            """SELECT count(*) FROM "Project"
                WHERE "Judging_Eligible" IS NOT NULL
                   OR "Voting_Eligible" IS NOT NULL
                   OR ("Award_Groups" IS NOT NULL
                       AND CAST("Award_Groups" AS TEXT) NOT IN ('null', '[]'))"""
        )
    ):
        raise RuntimeError(
            "Archive eligibility decisions before downgrading this revision"
        )
    if connection.scalar(
        sa.text('SELECT count(*) FROM "Rubric" WHERE "Is_Locked" = TRUE')
    ):
        raise RuntimeError("Archive confirmed rubrics before downgrading this revision")
    for table in (
        "Ballot_Selection",
        "Ballot",
        "Voter",
        "Voting_Round",
        "Competition_Settings",
        "Judge_Conflict",
    ):
        if connection.scalar(sa.text(f'SELECT count(*) FROM "{table}"')):
            raise RuntimeError(
                "Archive competition data before downgrading this revision"
            )
    for table in (
        "Ballot_Selection",
        "Ballot",
        "Voter",
        "Voting_Round",
        "Judge_Conflict",
        "Competition_Settings",
    ):
        op.drop_table(table)
    with op.batch_alter_table("Rubric") as batch:
        batch.drop_column("Is_Locked")
    with op.batch_alter_table("Project") as batch:
        for column in ("Judging_Eligible", "Voting_Eligible", "Award_Groups"):
            batch.drop_column(column)
