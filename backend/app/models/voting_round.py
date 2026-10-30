"""A voting round stays in draft until an organizer confirms all ballot rules."""

import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VotingRound(Base):
    __tablename__ = "Voting_Round"

    Round_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Event_ID: Mapped[str] = mapped_column(sa.ForeignKey("Event.Event_ID"))
    Round_Name: Mapped[str] = mapped_column(sa.String(200))
    Status: Mapped[str] = mapped_column(
        sa.String(20), default="draft", server_default="draft"
    )
    Candidate_Type: Mapped[str] = mapped_column(
        sa.String(20), default="poster", server_default="poster"
    )
    Trainees_Only: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    Min_Choices: Mapped[int | None] = mapped_column(sa.Integer)
    Max_Choices: Mapped[int | None] = mapped_column(sa.Integer)
    Ranked: Mapped[bool | None] = mapped_column(sa.Boolean)
    Allow_Self_Votes: Mapped[bool | None] = mapped_column(sa.Boolean)
    Allow_Edits: Mapped[bool | None] = mapped_column(sa.Boolean)
    Opens_At: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    Closes_At: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    Rules_Confirmed: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
