"""Selection order records rank only for an explicitly ranked round."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BallotSelection(Base):
    __tablename__ = "Ballot_Selection"

    Selection_ID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Ballot_ID: Mapped[str] = mapped_column(sa.ForeignKey("Ballot.Ballot_ID"))
    Project_ID: Mapped[str] = mapped_column(sa.ForeignKey("Project.Project_ID"))
    Rank: Mapped[int | None] = mapped_column(sa.Integer)
    __table_args__ = (
        sa.UniqueConstraint("Ballot_ID", "Project_ID", name="uq_ballot_selection"),
    )
