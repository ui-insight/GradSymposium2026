"""RubricCriterion model — individual scoring criterion within a rubric."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RubricCriterion(Base):
    __tablename__ = "Rubric_Criterion"

    Criterion_ID: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    Rubric_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Rubric.Rubric_ID"), nullable=False
    )
    Criterion_Name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    Criterion_Group: Mapped[str | None] = mapped_column(
        sa.String(100), nullable=True
    )
    Description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Min_Score: Mapped[int] = mapped_column(
        sa.Integer, default=0, server_default="0"
    )
    Max_Score: Mapped[int] = mapped_column(
        sa.Integer, default=3, server_default="3"
    )
    Sort_Order: Mapped[int] = mapped_column(
        sa.Integer, default=0, server_default="0"
    )

    rubric: Mapped["Rubric"] = relationship("Rubric", back_populates="criteria")  # noqa: F821
