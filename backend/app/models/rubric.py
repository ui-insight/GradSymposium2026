"""Rubric model — a scoring rubric for a category (Art or Poster)."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Rubric(Base):
    __tablename__ = "Rubric"

    Rubric_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Event_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Event.Event_ID"), nullable=False
    )
    Rubric_Name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Category: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    Max_Score: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    Description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    criteria: Mapped[list["RubricCriterion"]] = relationship(  # noqa: F821
        "RubricCriterion",
        back_populates="rubric",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RubricCriterion.Sort_Order",
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "Event_ID", "Category", name="uq_rubric_per_category_per_event"
        ),
        sa.CheckConstraint("Category IN ('Poster', 'Art')", name="ck_rubric_category"),
    )
