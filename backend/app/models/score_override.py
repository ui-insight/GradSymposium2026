"""Audit log for admin overrides to individual score rows."""

import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ScoreOverride(Base):
    __tablename__ = "Score_Override"

    Override_ID: Mapped[int] = mapped_column(
        sa.Integer, primary_key=True, autoincrement=True
    )
    Score_ID: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("Score.Score_ID"), nullable=False
    )
    Admin_User_ID: Mapped[str] = mapped_column(
        sa.String(36), sa.ForeignKey("User.User_ID"), nullable=False
    )
    Old_Score_Value: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    New_Score_Value: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    Overridden_At: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime,
        default=lambda: datetime.datetime.utcnow(),
        server_default=sa.func.now(),
    )

