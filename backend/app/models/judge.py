"""Judge model — an event judge who scores projects."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Judge(Base):
    __tablename__ = "Judge"

    Judge_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Event_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Event.Event_ID"), nullable=False
    )
    First_Name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Last_Name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Email: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    Department: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    Access_Code: Mapped[str] = mapped_column(
        sa.String(10), unique=True, nullable=False
    )
    Is_Active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default="1"
    )

    scores: Mapped[list["Score"]] = relationship(  # noqa: F821
        "Score", back_populates="judge", cascade="all, delete-orphan", lazy="selectin"
    )
    assignments: Mapped[list["JudgeAssignment"]] = relationship(  # noqa: F821
        "JudgeAssignment",
        back_populates="judge",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
