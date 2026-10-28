"""Organizer-confirmed judging rules. Absence preserves legacy event behavior."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompetitionSettings(Base):
    __tablename__ = "Competition_Settings"

    Event_ID: Mapped[str] = mapped_column(
        sa.ForeignKey("Event.Event_ID"), primary_key=True
    )
    Is_Rehearsal: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    Required_Reviews: Mapped[int | None] = mapped_column(sa.Integer)
    Assignment_Only: Mapped[bool | None] = mapped_column(sa.Boolean)
    Aggregation: Mapped[str | None] = mapped_column(sa.String(20))
    Tie_Policy: Mapped[str | None] = mapped_column(sa.String(20))
    Award_Groups: Mapped[list | None] = mapped_column(sa.JSON)
    Rules_Confirmed: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    Judging_Open: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
