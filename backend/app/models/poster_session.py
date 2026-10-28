"""Optional, explicitly confirmed odd/even convention for one event."""

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PosterSession(Base):
    __tablename__ = "Poster_Session"

    Event_ID: Mapped[str] = mapped_column(
        sa.ForeignKey("Event.Event_ID"), primary_key=True
    )
    Odd_Session: Mapped[str] = mapped_column(sa.String(2), nullable=False)
    Session_I_Time: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    Session_II_Time: Mapped[str] = mapped_column(sa.String(150), nullable=False)
    Reference: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    Confirmed_By: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    Confirmed_At: Mapped[datetime.datetime] = mapped_column(sa.DateTime)

    __table_args__ = (sa.CheckConstraint("\"Odd_Session\" IN ('I', 'II')"),)
