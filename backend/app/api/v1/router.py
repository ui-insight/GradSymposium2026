"""Top-level API v1 router."""

from fastapi import APIRouter

from app.api.v1.assignments import router as assignments_router
from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.judge_portal import router as judge_router
from app.api.v1.judges import router as judges_router
from app.api.v1.projects import router as projects_router
from app.api.v1.results import router as results_router
from app.api.v1.rubrics import router as rubrics_router
from app.api.v1.scores import router as scores_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(events_router)
api_router.include_router(projects_router)
api_router.include_router(judges_router)
api_router.include_router(rubrics_router)
api_router.include_router(scores_router)
api_router.include_router(results_router)
api_router.include_router(assignments_router)
api_router.include_router(judge_router)


@api_router.get("/health")
async def health_check():
    return {"status": "ok"}
