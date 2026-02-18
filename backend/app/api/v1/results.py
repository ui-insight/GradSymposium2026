"""Results and export routes (admin only)."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.user import User
from app.schemas.results import EventSummary, ProjectResult
from app.services.excel_export import export_results_to_excel
from app.services.results_service import get_event_summary, get_project_results

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/", response_model=list[ProjectResult])
async def get_results(
    event_id: str,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await get_project_results(db, event_id, category)


@router.get("/summary", response_model=EventSummary)
async def get_summary(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await get_event_summary(db, event_id)


@router.get("/export")
async def export_results(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    poster_results = await get_project_results(db, event_id, "Poster")
    art_results = await get_project_results(db, event_id, "Art")
    buf = export_results_to_excel(poster_results, art_results)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=symposium_results.xlsx"},
    )
