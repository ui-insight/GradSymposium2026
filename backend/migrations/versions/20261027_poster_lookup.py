"""Add draft/publication metadata and permanent poster number reservations.

Revision ID: 20261027_poster_lookup
Revises: None (the existing app creates its base tables on startup)
"""

import sqlalchemy as sa
from alembic import op

from app.db.base import Base
from app.models.project_number_reservation import ProjectNumberReservation

revision = "20261027_poster_lookup"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if not sa.inspect(connection).has_table("Event"):
        # The container runs Alembic before the app's create_all on a fresh volume.
        Base.metadata.create_all(connection)
        return
    for table, column in (
        ("Event", sa.Column("Event_End_Date", sa.Date(), nullable=True)),
        (
            "Event",
            sa.Column(
                "Public_Poster_Lookup_Enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        ),
        ("Project", sa.Column("Presenter_Display_Name", sa.String(300), nullable=True)),
        ("Project", sa.Column("Institution", sa.String(200), nullable=True)),
        (
            "Project",
            sa.Column(
                "Is_Published", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        ),
    ):
        names = {item["name"] for item in sa.inspect(connection).get_columns(table)}
        if column.name not in names:
            op.add_column(table, column)
    ProjectNumberReservation.__table__.create(connection, checkfirst=True)


def downgrade() -> None:
    op.drop_table("Project_Number_Reservation")
    for table, columns in (
        ("Project", ["Is_Published", "Institution", "Presenter_Display_Name"]),
        ("Event", ["Public_Poster_Lookup_Enabled", "Event_End_Date"]),
    ):
        with op.batch_alter_table(table) as batch:
            for column in columns:
                batch.drop_column(column)
