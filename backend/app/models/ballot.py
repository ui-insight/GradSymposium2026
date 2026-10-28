"""One saved ballot per voter per round, including after credential replacement."""

import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Ballot(Base):
    __tablename__ = "Ballot"

    Ballot_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Round_ID: Mapped[str] = mapped_column(sa.ForeignKey("Voting_Round.Round_ID"))
    Voter_ID: Mapped[str] = mapped_column(sa.ForeignKey("Voter.Voter_ID"))
    Submitted_At: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    Updated_At: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    __table_args__ = (
        sa.UniqueConstraint("Round_ID", "Voter_ID", name="uq_ballot_entitlement"),
    )
