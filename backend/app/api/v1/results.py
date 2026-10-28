"""Results and export routes (admin only)."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.judge import Judge
from app.models.project import Project
from app.models.user import User
from app.schemas.results import EventSummary, ProjectResult
from app.services.excel_export import export_results_to_excel
from app.services.results_service import get_event_summary, get_project_results

router = APIRouter(prefix="/results", tags=["results"])


@router.get("/", response_model=list[ProjectResult])
async def get_results(
    event_id: str,
    category: str | None = None,
    award_group: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await get_project_results(db, event_id, category, award_group)


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
    award_group: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    poster_results = await get_project_results(db, event_id, "Poster", award_group)
    art_results = await get_project_results(db, event_id, "Art", award_group)
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
    from app.models.competition import CompetitionSettings
    from app.services.competition import complete_reviews

    rules = await db.get(CompetitionSettings, event_id)
    projects = {
        p.Project_ID: p
        for p in await db.scalars(
            select(Project).where(
                Project.Event_ID == event_id, Project.Is_Active.is_(True)
            )
        )
    }
    judges = {
        j.Judge_ID: j
        for j in await db.scalars(select(Judge).where(Judge.Event_ID == event_id))
    }
    reviews = [
        r
        for r in await complete_reviews(db, event_id)
        if r["Project_ID"] in projects
        and (not rules or projects[r["Project_ID"]].Judging_Eligible is True)
    ]
    reviews.sort(key=lambda r: r["Scored_At"], reverse=True)
    return [
        {
            "Judge_Name": (
                f"{judges[r['Judge_ID']].First_Name} {judges[r['Judge_ID']].Last_Name}"
            ),
            "Project_Number": projects[r["Project_ID"]].Project_Number,
            "Project_Title": projects[r["Project_ID"]].Project_Title,
            "Category": projects[r["Project_ID"]].Category,
            "Total_Score": r["Total_Score"],
            "Scored_At": r["Scored_At"].isoformat(),
        }
        for r in reviews[: max(1, min(limit, 100))]
    ]
