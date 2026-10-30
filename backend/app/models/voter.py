"""One voter entitlement per event. Only a hash of the random access code persists."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Voter(Base):
    __tablename__ = "Voter"

    Voter_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Event_ID: Mapped[str] = mapped_column(sa.ForeignKey("Event.Event_ID"))
    Registration_Reference: Mapped[str] = mapped_column(sa.String(200))
    Code_Hash: Mapped[str] = mapped_column(sa.String(64), unique=True)
    Credential_Version: Mapped[int] = mapped_column(
        sa.Integer, default=1, server_default="1"
    )
    Is_Active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.true()
    )
    Is_Trainee: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    Talk_Affiliation_Confirmed: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    Presenter_Talk_IDs: Mapped[list] = mapped_column(
        sa.JSON, default=list, server_default="[]"
    )
    Affiliation_Confirmed: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    Presenter_Project_IDs: Mapped[list] = mapped_column(sa.JSON, default=list)
    __table_args__ = (
        sa.UniqueConstraint(
            "Event_ID", "Registration_Reference", name="uq_voter_registration"
        ),
    )
