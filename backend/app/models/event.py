"""Event model — a single symposium event."""

import datetime
import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Event(Base):
    __tablename__ = "Event"

    Event_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Event_Name: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    Event_Date: Mapped[datetime.date] = mapped_column(sa.Date, nullable=False)
    Location: Mapped[str | None] = mapped_column(sa.String(200), nullable=True)
    Description: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    Is_Active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.text("true")
    )
    Created_At: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default=lambda: datetime.datetime.utcnow(),
        server_default=sa.func.now(),
    )
