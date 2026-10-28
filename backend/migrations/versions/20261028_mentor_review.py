"""Store organizer mentor-review decisions without changing existing conflicts."""

import sqlalchemy as sa
from alembic import op

from app.models.mentor_review import MentorReview

revision = "20261028_mentor_review"
down_revision = "20261028_judge_profile"
branch_labels = None
depends_on = None


def upgrade():
    MentorReview.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT count(*) FROM "Mentor_Review"')):
        raise RuntimeError("Archive mentor review decisions before downgrade")
    op.drop_table("Mentor_Review")
