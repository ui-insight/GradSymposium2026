"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import settings
from app.db.base import Base
from app.db.engine import engine
from app.db.seed import seed_database
from app.db.engine import async_session_factory

# Ensure all models are imported so create_all sees them
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
