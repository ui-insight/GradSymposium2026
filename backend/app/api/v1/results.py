"""Results and export routes (admin only)."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.judge import Judge
from app.models.project import Project
from app.models.score import Score
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


@router.get("/activity")
async def recent_activity(
    event_id: str,
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Get the most recent score submissions (unique judge-project pairs)."""
    stmt = (
        select(
            Score.Judge_ID,
            Score.Project_ID,
            func.max(Score.Scored_At).label("last_scored"),
            func.sum(Score.Score_Value).label("total"),
            func.count(Score.Score_ID).label("criteria_count"),
            Judge.First_Name.label("judge_first"),
            Judge.Last_Name.label("judge_last"),
            Project.Project_Number,
            Project.Project_Title,
            Project.Category,
        )
        .join(Judge, Score.Judge_ID == Judge.Judge_ID)
        .join(Project, Score.Project_ID == Project.Project_ID)
        .where(Project.Event_ID == event_id)
        .group_by(
            Score.Judge_ID,
            Score.Project_ID,
            Judge.First_Name,
            Judge.Last_Name,
            Project.Project_Number,
            Project.Project_Title,
            Project.Category,
        )
        .order_by(func.max(Score.Scored_At).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "Judge_Name": f"{r.judge_first} {r.judge_last}",
            "Project_Number": r.Project_Number,
            "Project_Title": r.Project_Title,
            "Category": r.Category,
            "Total_Score": r.total,
            "Scored_At": r.last_scored.isoformat() if r.last_scored else None,
        }
        for r in rows
    ]
