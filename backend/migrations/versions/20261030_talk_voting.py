"""Separate talk ballots and round-specific trainee access."""

import sqlalchemy as sa
from alembic import op

from app.db.schema import _ensure_runtime_schema_sync
from app.models.talk import TalkBallot, TalkCandidate

revision = "20261030_talk_voting"
down_revision = "20261028_poster_sessions"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    _ensure_runtime_schema_sync(connection)
    TalkCandidate.__table__.create(connection, checkfirst=True)
    TalkBallot.__table__.create(connection, checkfirst=True)


def downgrade():
    connection = op.get_bind()
    for table in (TalkBallot.__table__, TalkCandidate.__table__):
        if connection.scalar(sa.select(sa.func.count()).select_from(table)):
            raise RuntimeError("Preserve talk candidates and ballots before downgrade")
    if connection.scalar(
        sa.text(
            'SELECT count(*) FROM "Voter" WHERE "Is_Trainee" = TRUE '
            'OR "Talk_Affiliation_Confirmed" = TRUE '
            'OR CAST("Presenter_Talk_IDs" AS TEXT) != \'[]\''
        )
    ):
        raise RuntimeError("Preserve talk voter eligibility before downgrade")
    if connection.scalar(
        sa.text(
            'SELECT count(*) FROM "Voting_Round" WHERE "Candidate_Type" != \'poster\' '
            'OR "Trainees_Only" = TRUE'
        )
    ):
        raise RuntimeError("Preserve talk round settings before downgrade")
    TalkBallot.__table__.drop(connection)
    TalkCandidate.__table__.drop(connection)
    for table, columns in (
        ("Voter", ["Is_Trainee", "Talk_Affiliation_Confirmed", "Presenter_Talk_IDs"]),
        ("Voting_Round", ["Candidate_Type", "Trainees_Only"]),
    ):
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.drop_column(column)
