"""JudgeAssignment model — optional pre-assignment of judges to projects."""

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JudgeAssignment(Base):
    __tablename__ = "Judge_Assignment"

    Assignment_ID: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    Judge_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Judge.Judge_ID"), nullable=False
    )
    Project_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Project.Project_ID"), nullable=False
    )
    Assigned_At: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        server_default=sa.func.now(),
    )

    judge: Mapped["Judge"] = relationship("Judge", back_populates="assignments")  # noqa: F821
    project: Mapped["Project"] = relationship("Project", lazy="selectin")  # noqa: F821

    __table_args__ = (
        sa.UniqueConstraint(
            "Judge_ID", "Project_ID", name="uq_assignment_per_judge_project"
        ),
    )
