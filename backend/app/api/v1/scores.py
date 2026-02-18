"""Score viewing/management routes (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.project import Project
from app.models.score import Score
from app.models.user import User
from app.schemas.score import ScoreRead

router = APIRouter(prefix="/scores", tags=["scores"])


@router.get("/", response_model=list[ScoreRead])
async def list_scores(
    event_id: str,
    judge_id: str | None = None,
    project_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    stmt = (
        select(Score)
        .join(Project, Score.Project_ID == Project.Project_ID)
        .where(Project.Event_ID == event_id)
    )
    if judge_id:
        stmt = stmt.where(Score.Judge_ID == judge_id)
    if project_id:
        stmt = stmt.where(Score.Project_ID == project_id)
    stmt = stmt.order_by(Score.Scored_At.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{score_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_score(
    score_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Score).where(Score.Score_ID == score_id))
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    await db.delete(score)
    await db.commit()
