"""Project model — a student presentation entry."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "Project"

    Project_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Event_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("Event.Event_ID"), nullable=False
    )
    Project_Number: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    Project_Title: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    Presenter_First_Name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Presenter_Last_Name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Presenter_Email: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    Presenter_Display_Name: Mapped[str | None] = mapped_column(sa.String(300))
    Institution: Mapped[str | None] = mapped_column(sa.String(200))
    Source_Submission_Key: Mapped[str | None] = mapped_column(sa.String(128))
    Roster_Review: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    Roster_Review_Required: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    Is_Published: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    Department: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    College: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    Advisor_Name: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    Category: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    Table_Number: Mapped[str | None] = mapped_column(sa.String(20), nullable=True)
    Is_Active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.text("true")
    )

    scores: Mapped[list["Score"]] = relationship(  # noqa: F821
        "Score", back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        sa.Index(
            "uq_project_source_submission",
            "Event_ID",
            "Source_Submission_Key",
            unique=True,
        ),
        sa.UniqueConstraint(
            "Event_ID", "Project_Number", name="uq_project_number_per_event"
        ),
        sa.CheckConstraint(
            "\"Category\" IN ('Poster', 'Art')", name="ck_project_category"
        ),
    )
