"""Issued numbers remain reserved even if their project is deleted."""

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProjectNumberReservation(Base):
    __tablename__ = "Project_Number_Reservation"

    Reservation_ID: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    Event_ID: Mapped[str] = mapped_column(sa.ForeignKey("Event.Event_ID"))
    Project_Number: Mapped[str] = mapped_column(sa.String(20))
    Project_ID: Mapped[str] = mapped_column(sa.String(36))

    __table_args__ = (
        sa.UniqueConstraint("Event_ID", "Project_Number", name="uq_reserved_number"),
    )
