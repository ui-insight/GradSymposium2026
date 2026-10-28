"""Organizer relationship decisions, separate from conflict enforcement."""

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MentorReview(Base):
    __tablename__ = "Mentor_Review"

    Review_ID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Judge_ID: Mapped[str] = mapped_column(sa.ForeignKey("Judge.Judge_ID"))
    Project_ID: Mapped[str] = mapped_column(sa.ForeignKey("Project.Project_ID"))
    Decision: Mapped[str] = mapped_column(sa.String(20))
    Note: Mapped[str] = mapped_column(sa.String(500))
    Source_Context: Mapped[str] = mapped_column(sa.String(64))
    Reviewed_By: Mapped[str] = mapped_column(sa.String(100))
    Reviewed_At: Mapped[datetime.datetime] = mapped_column(sa.DateTime)
    __table_args__ = (
        sa.UniqueConstraint("Judge_ID", "Project_ID", name="uq_mentor_review"),
        sa.CheckConstraint(
            "\"Decision\" IN ('clear', 'conflict', 'needs_input')",
            name="ck_mentor_review_decision",
        ),
    )
