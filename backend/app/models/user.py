"""User model — admin accounts only."""

import uuid

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "User"

    User_ID: Mapped[str] = mapped_column(
        sa.String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    Username: Mapped[str] = mapped_column(
        sa.String(100), unique=True, nullable=False
    )
    Hashed_Password: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    Role: Mapped[str] = mapped_column(
        sa.String(50), default="admin", server_default="admin"
    )
    Is_Active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.text("true")
    )
