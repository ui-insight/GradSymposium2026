"""Personal judge QR invitations and optional public browser voting."""

import sqlalchemy as sa
from alembic import op

from app.db.schema import _ensure_runtime_schema_sync
from app.models.judge_invite import JudgeInvite

revision = "20261030_qr_checkin"
down_revision = "20261030_talk_voting"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    _ensure_runtime_schema_sync(connection)
    JudgeInvite.__table__.create(connection, checkfirst=True)


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.select(sa.func.count()).select_from(JudgeInvite)):
        raise RuntimeError("Preserve personal judge invitations before downgrade")
    for table, column in (
        ("Voter", "Browser_Only"),
        ("Voting_Round", "Public_Browser"),
    ):
        if connection.scalar(
            sa.text(f'SELECT count(*) FROM "{table}" WHERE "{column}" = TRUE')
        ):
            raise RuntimeError("Preserve browser voting state before downgrade")
    JudgeInvite.__table__.drop(connection)
    for table, column in (
        ("Voter", "Browser_Only"),
        ("Voting_Round", "Public_Browser"),
    ):
        with op.batch_alter_table(table) as batch:
            batch.drop_column(column)
