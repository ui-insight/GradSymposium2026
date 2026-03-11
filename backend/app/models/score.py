"""Score model — one score per judge + project + criterion."""

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Score(Base):
    __tablename__ = "Score"

    Score_ID: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    Judge_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Judge.Judge_ID"), nullable=False
    )
    Project_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Project.Project_ID"), nullable=False
    )
    Criterion_ID: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("Rubric_Criterion.Criterion_ID"), nullable=False
    )
    Score_Value: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    Scored_At: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default=lambda: datetime.datetime.utcnow(),
        server_default=sa.func.now(),
    )

    judge: Mapped["Judge"] = relationship("Judge", back_populates="scores")  # noqa: F821
    project: Mapped["Project"] = relationship("Project", back_populates="scores")  # noqa: F821
    criterion: Mapped["RubricCriterion"] = relationship("RubricCriterion", lazy="selectin")  # noqa: F821

    __table_args__ = (
        sa.UniqueConstraint(
            "Judge_ID",
            "Project_ID",
            "Criterion_ID",
            name="uq_score_per_judge_project_criterion",
        ),
        sa.CheckConstraint(
            "\"Score_Value\" >= 0 AND \"Score_Value\" <= 3", name="ck_score_range"
        ),
    )
