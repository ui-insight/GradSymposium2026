"""Admin-issued personal invitations; unclaimed judges remain inactive."""

import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JudgeInvite(Base):
    __tablename__ = "Judge_Invite"
    Invite_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Event_ID: Mapped[str] = mapped_column(sa.ForeignKey("Event.Event_ID"))
    Judge_ID: Mapped[str] = mapped_column(
        sa.ForeignKey("Judge.Judge_ID", ondelete="CASCADE"), unique=True
    )
    Assignment_Limit: Mapped[int] = mapped_column(sa.Integer, default=12)
    Issued_At: Mapped[datetime.datetime] = mapped_column(sa.DateTime(timezone=True))

    Activated_At: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
