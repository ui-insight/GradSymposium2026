"""Optional confirmed poster board/session convention; no seeded mapping."""

import sqlalchemy as sa
from alembic import op

from app.models.poster_session import PosterSession

revision = "20261028_poster_sessions"
down_revision = "20261028_final_roster"
branch_labels = None
depends_on = None


def upgrade():
    PosterSession.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM "Poster_Session"')):
        raise RuntimeError("Archive confirmed poster sessions before downgrade")
    op.drop_table("Poster_Session")
