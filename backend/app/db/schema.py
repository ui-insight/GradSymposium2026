"""Runtime schema fixes for existing databases."""

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncConnection


async def ensure_runtime_schema(conn: AsyncConnection) -> None:
    """Backfill columns that older databases may be missing."""

    await conn.run_sync(_ensure_runtime_schema_sync)


def _ensure_runtime_schema_sync(sync_conn) -> None:
    inspector = inspect(sync_conn)
    dialect = sync_conn.dialect.name
    default_true = "TRUE" if dialect == "postgresql" else "1"

    default_false = "FALSE" if dialect == "postgresql" else "0"
    for table, name, definition in (
        ("Event", "Event_End_Date", "DATE"),
        (
            "Event",
            "Public_Poster_Lookup_Enabled",
            f"BOOLEAN NOT NULL DEFAULT {default_false}",
        ),
        ("Project", "Presenter_Display_Name", "VARCHAR(300)"),
        ("Project", "Institution", "VARCHAR(200)"),
        ("Project", "Judging_Eligible", "BOOLEAN"),
        ("Project", "Voting_Eligible", "BOOLEAN"),
        ("Project", "Award_Groups", "JSON"),
        ("Project", "Is_Published", f"BOOLEAN NOT NULL DEFAULT {default_false}"),
        ("Project", "Source_Submission_Key", "VARCHAR(128)"),
        ("Project", "Roster_Review", "JSON"),
        (
            "Project",
            "Roster_Review_Required",
            f"BOOLEAN NOT NULL DEFAULT {default_false}",
        ),
    ):
        _ensure_column(sync_conn, inspector, table, name, f'"{name}" {definition}')

    if inspector.has_table("Rubric"):
        _ensure_column(
            sync_conn, inspector, "Rubric", "Score_Labels", '"Score_Labels" JSON'
        )
        _ensure_column(
            sync_conn,
            inspector,
            "Rubric",
            "Is_Locked",
            f'"Is_Locked" BOOLEAN NOT NULL DEFAULT {default_false}',
        )

    if inspector.has_table("Judge"):
        for name, definition in (
            ("Name_Confirmed_At", "TIMESTAMP"),
            ("Previous_Name", "VARCHAR(201)"),
            ("Conflict_Review_Required", f"BOOLEAN NOT NULL DEFAULT {default_false}"),
        ):
            _ensure_column(
                sync_conn, inspector, "Judge", name, f'"{name}" {definition}'
            )

    # create_all does not add indexes to an existing table.
    from app.models.project import Project

    for index in Project.__table__.indexes:
        if index.name == "uq_project_source_submission":
            index.create(sync_conn, checkfirst=True)

    _ensure_column(
        sync_conn,
        inspector,
        table_name="Score",
        column_name="Is_Active",
        column_sql=f'"Is_Active" BOOLEAN NOT NULL DEFAULT {default_true}',
    )
    _ensure_column(
        sync_conn,
        inspector,
        table_name="Feedback",
        column_name="Is_Active",
        column_sql=f'"Is_Active" BOOLEAN NOT NULL DEFAULT {default_true}',
    )

    from app.db.score_scale import ensure_score_range

    ensure_score_range(sync_conn)


def _ensure_column(
    sync_conn,
    inspector,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        return

    sync_conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN {column_sql}'))
