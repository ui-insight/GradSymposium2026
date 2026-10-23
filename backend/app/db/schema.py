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
