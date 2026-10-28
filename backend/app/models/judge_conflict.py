"""Explicit organizer-recorded conflicts; never infer them from institutions."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JudgeConflict(Base):
    __tablename__ = "Judge_Conflict"

    Conflict_ID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Judge_ID: Mapped[str] = mapped_column(sa.ForeignKey("Judge.Judge_ID"))
    Project_ID: Mapped[str] = mapped_column(sa.ForeignKey("Project.Project_ID"))
    Reason: Mapped[str] = mapped_column(sa.String(500))
    __table_args__ = (
        sa.UniqueConstraint("Judge_ID", "Project_ID", name="uq_judge_conflict"),
    )
