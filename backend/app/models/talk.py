"""Talk candidates and ballots stay separate from poster identities and scores."""

import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TalkCandidate(Base):
    __tablename__ = "Talk_Candidate"
    Candidate_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Round_ID: Mapped[str] = mapped_column(sa.ForeignKey("Voting_Round.Round_ID"))
    Presenter_Display_Name: Mapped[str] = mapped_column(sa.String(300))
    Institution: Mapped[str | None] = mapped_column(sa.String(200))
    Project_Title: Mapped[str] = mapped_column(sa.String(500), default="")
    Is_Active: Mapped[bool] = mapped_column(sa.Boolean, default=True)

    @property
    def Project_ID(self):
        return self.Candidate_ID

    @property
    def Project_Number(self):
        return ""


class TalkBallot(Base):
    __tablename__ = "Talk_Ballot"
    Ballot_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Round_ID: Mapped[str] = mapped_column(sa.ForeignKey("Voting_Round.Round_ID"))
    Voter_ID: Mapped[str] = mapped_column(sa.ForeignKey("Voter.Voter_ID"))
    Candidate_IDs: Mapped[list] = mapped_column(sa.JSON)
    Submitted_At: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))
    Updated_At: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))
    __table_args__ = (
        sa.UniqueConstraint("Round_ID", "Voter_ID", name="uq_talk_ballot"),
    )
