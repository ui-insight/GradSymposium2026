"""Upgrade the score envelope without changing any rubric's scoring rules."""

import re

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect


def ensure_score_range(connection, maximum=5):
    inspector = inspect(connection)
    if not inspector.has_table("Score") or "Score_Value" not in {
        column["name"] for column in inspector.get_columns("Score")
    }:
        return
    constraint = next(
        (
            item
            for item in inspector.get_check_constraints("Score")
            if item["name"] == "ck_score_range"
        ),
        None,
    )
    expected = f"score_value>=0andscore_value<={maximum}"
    if constraint and re.sub(r'[\s"()]', "", constraint["sqltext"].lower()) == expected:
        return
    # SQLite batch migration replaces the table. Never disable referential
    # integrity inside an active transaction or risk losing audit references.
    if (
        connection.dialect.name == "sqlite"
        and connection.exec_driver_sql("PRAGMA foreign_keys").scalar()
    ):
        raise RuntimeError(
            "Run 'alembic upgrade head' before startup to upgrade the SQLite "
            "score constraint; its migration connection must have foreign_keys OFF"
        )
    operations = Operations(MigrationContext.configure(connection))
    with operations.batch_alter_table("Score") as batch:
        if constraint:
            batch.drop_constraint("ck_score_range", type_="check")
        batch.create_check_constraint(
            "ck_score_range", f'"Score_Value" >= 0 AND "Score_Value" <= {maximum}'
        )
