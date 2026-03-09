"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api.v1.router import api_router  # noqa: E402
from app.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.engine import async_session_factory, engine  # noqa: E402
from app.db.seed import seed_database  # noqa: E402

# Ensure all models are imported so create_all sees them
import app.models  # noqa: F401, E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.check_security()

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Stamp Alembic head so future migrations start from current schema
    from alembic.config import Config
    from alembic.migration import MigrationContext
    from alembic.script import ScriptDirectory

    alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    script = ScriptDirectory.from_config(alembic_cfg)

    async with engine.begin() as conn:

        def _stamp(sync_conn):
            ctx = MigrationContext.configure(sync_conn)
            ctx.stamp(script, "head")

        await conn.run_sync(_stamp)

    # Seed dev data
    if settings.dev_mode:
        async with async_session_factory() as session:
            await seed_database(session)

    yield


app = FastAPI(
    title="GradSymposium2026",
    description="GPSA Graduate Student Symposium Judging Application",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
