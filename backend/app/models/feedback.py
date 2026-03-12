"""Feedback model — optional judge feedback per project."""

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Feedback(Base):
    __tablename__ = "Feedback"

    Feedback_ID: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    Judge_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Judge.Judge_ID"), nullable=False
    )
    Project_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Project.Project_ID"), nullable=False
    )
    Feedback_Text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    Created_At: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default=lambda: datetime.datetime.utcnow(),
        server_default=sa.func.now(),
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "Judge_ID", "Project_ID", name="uq_feedback_per_judge_project"
        ),
    )
