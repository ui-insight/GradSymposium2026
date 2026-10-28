"""Preserve final roster decisions and exact-content organizer sign-offs."""

import sqlalchemy as sa
from alembic import op

from app.models.roster_review import RosterDecision, RosterSignoff

revision = "20261028_final_roster"
down_revision = "20261028_mentor_review"
branch_labels = None
depends_on = None


def upgrade():
    for model in (RosterDecision, RosterSignoff):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in ("Roster_Decision", "Roster_Signoff"):
        if op.get_bind().scalar(sa.text(f'SELECT count(*) FROM "{table}"')):
            raise RuntimeError(
                "Archive final roster decisions/sign-offs before downgrade"
            )
    op.drop_table("Roster_Signoff")
    op.drop_table("Roster_Decision")
