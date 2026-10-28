"""Append-only roster decisions and organizer sign-offs of an exact roster."""

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RosterDecision(Base):
    __tablename__ = "Roster_Decision"
    Decision_ID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Project_ID: Mapped[str] = mapped_column(
        sa.ForeignKey("Project.Project_ID"), index=True
    )
    Decision: Mapped[str] = mapped_column(sa.String(20))
    Reason: Mapped[str] = mapped_column(sa.String(500))
    Source_Context: Mapped[str] = mapped_column(sa.String(64))
    Snapshot: Mapped[dict] = mapped_column(sa.JSON)
    Superseded_By: Mapped[str | None] = mapped_column(
        sa.ForeignKey("Project.Project_ID")
    )
    Recorded_By: Mapped[str] = mapped_column(sa.String(100))
    Recorded_At: Mapped[datetime.datetime] = mapped_column(sa.DateTime)
    __table_args__ = (
        sa.CheckConstraint(
            "\"Decision\" IN ('accepted', 'withdrawn', 'pending')",
            name="ck_roster_decision",
        ),
    )


class RosterSignoff(Base):
    __tablename__ = "Roster_Signoff"
    Signoff_ID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Event_ID: Mapped[str] = mapped_column(sa.ForeignKey("Event.Event_ID"), index=True)
    Context: Mapped[str] = mapped_column(sa.String(64))
    Accepted_Count: Mapped[int] = mapped_column()
    Source_Count: Mapped[int] = mapped_column()
    Reference: Mapped[str] = mapped_column(sa.String(500))
    Snapshot: Mapped[dict] = mapped_column(sa.JSON)
    Signed_By: Mapped[str] = mapped_column(sa.String(100))
    Signed_At: Mapped[datetime.datetime] = mapped_column(sa.DateTime)
