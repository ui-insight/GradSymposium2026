"""Judge-facing portal routes (access code auth)."""

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_judge, get_db
from app.auth.jwt import create_access_token
from app.models.feedback import Feedback
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.project import Project
from app.models.rubric import Rubric
from app.models.score import Score
from app.schemas.auth import JudgeLogin, TokenResponse
from app.schemas.score import ScoreSubmission

router = APIRouter(prefix="/judge", tags=["judge-portal"])
log = logging.getLogger(__name__)


# --- Auth ---


@router.post("/login", response_model=TokenResponse)
async def judge_login(body: JudgeLogin, db: AsyncSession = Depends(get_db)):
    code = body.access_code.strip().upper()
    result = await db.execute(select(Judge).where(Judge.Access_Code == code))
    judge = result.scalar_one_or_none()
    if not judge:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access code",
        )
    if not judge.Is_Active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Judge account disabled"
        )
    token = create_access_token(subject=judge.Judge_ID, role="judge")
    return TokenResponse(access_token=token)


@router.get("/me")
async def judge_me(judge: Judge = Depends(get_current_judge)):
    return {
        "Judge_ID": judge.Judge_ID,
        "First_Name": judge.First_Name,
        "Last_Name": judge.Last_Name,
        "Event_ID": judge.Event_ID,
    }


# --- Projects ---


@router.get("/projects")
async def judge_projects(
    judge: Judge = Depends(get_current_judge),
    db: AsyncSession = Depends(get_db),
):
    """List projects available to score. Assigned projects first."""
    # Get assigned project IDs
    assign_result = await db.execute(
        select(JudgeAssignment.Project_ID).where(
            JudgeAssignment.Judge_ID == judge.Judge_ID
        )
    )
    assigned_ids = set(assign_result.scalars().all())

    # Get all active projects for this event
    proj_result = await db.execute(
        select(Project)
        .where(Project.Event_ID == judge.Event_ID, Project.Is_Active.is_(True))
        .order_by(Project.Category, Project.Project_Number)
    )
    projects = proj_result.scalars().all()

    # Get projects this judge has already scored
    scored_result = await db.execute(
        select(Score.Project_ID.distinct()).where(Score.Judge_ID == judge.Judge_ID)
    )
    scored_ids = set(scored_result.scalars().all())

    result = []
    for p in projects:
        result.append(
            {
                "Project_ID": p.Project_ID,
                "Project_Number": p.Project_Number,
                "Project_Title": p.Project_Title,
                "Presenter_First_Name": p.Presenter_First_Name,
                "Presenter_Last_Name": p.Presenter_Last_Name,
                "Department": p.Department,
                "Category": p.Category,
                "Table_Number": p.Table_Number,
                "is_assigned": p.Project_ID in assigned_ids,
                "is_scored": p.Project_ID in scored_ids,
            }
        )

    # Sort: assigned first, then by category and number
    result.sort(key=lambda x: (not x["is_assigned"], x["Category"], x["Project_Number"]))
    return result


@router.get("/projects/{project_id}")
async def judge_project_detail(
    project_id: str,
    judge: Judge = Depends(get_current_judge),
    db: AsyncSession = Depends(get_db),
):
    """Get project detail with rubric and any existing scores."""
    proj_result = await db.execute(
        select(Project).where(Project.Project_ID == project_id)
    )
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get the rubric for this category
    rubric_result = await db.execute(
        select(Rubric).where(
            Rubric.Event_ID == judge.Event_ID,
            Rubric.Category == project.Category,
        )
    )
    rubric = rubric_result.scalar_one_or_none()

    # Get existing scores by this judge for this project
    score_result = await db.execute(
        select(Score).where(
            Score.Judge_ID == judge.Judge_ID,
            Score.Project_ID == project_id,
        )
    )
    existing_scores = {s.Criterion_ID: s.Score_Value for s in score_result.scalars().all()}

    # Older dev databases may not have feedback storage yet.
    existing_feedback = None
    try:
        fb_result = await db.execute(
            select(Feedback).where(
                Feedback.Judge_ID == judge.Judge_ID,
                Feedback.Project_ID == project_id,
            )
        )
        existing_feedback = fb_result.scalar_one_or_none()
    except OperationalError:
        log.warning(
            "Feedback could not be loaded for judge %s project %s",
            judge.Judge_ID,
            project_id,
            exc_info=True,
        )

    rubric_data = None
    if rubric:
        rubric_data = {
            "Rubric_ID": rubric.Rubric_ID,
            "Rubric_Name": rubric.Rubric_Name,
            "Category": rubric.Category,
            "Max_Score": rubric.Max_Score,
            "criteria": [
                {
                    "Criterion_ID": c.Criterion_ID,
                    "Criterion_Name": c.Criterion_Name,
                    "Criterion_Group": c.Criterion_Group,
                    "Min_Score": c.Min_Score,
                    "Max_Score": c.Max_Score,
                    "Sort_Order": c.Sort_Order,
                }
                for c in rubric.criteria
            ],
        }

    return {
        "Project_ID": project.Project_ID,
        "Project_Number": project.Project_Number,
        "Project_Title": project.Project_Title,
        "Presenter_First_Name": project.Presenter_First_Name,
        "Presenter_Last_Name": project.Presenter_Last_Name,
        "Department": project.Department,
        "Category": project.Category,
        "Table_Number": project.Table_Number,
        "rubric": rubric_data,
        "existing_scores": existing_scores,
        "existing_feedback": existing_feedback.Feedback_Text if existing_feedback else None,
    }


@router.post("/projects/{project_id}/scores")
async def submit_scores(
    project_id: str,
    body: ScoreSubmission,
    judge: Judge = Depends(get_current_judge),
    db: AsyncSession = Depends(get_db),
):
    """Submit or update all criterion scores for a project."""
    # Verify project exists
    proj_result = await db.execute(
        select(Project).where(
            Project.Project_ID == project_id,
            Project.Event_ID == judge.Event_ID,
            Project.Is_Active.is_(True),
        )
    )
    if not proj_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    scored_at = datetime.datetime.utcnow()
    for entry in body.scores:
        if entry.Score_Value < 0 or entry.Score_Value > 3:
            raise HTTPException(
                status_code=400, detail=f"Score must be 0-3, got {entry.Score_Value}"
            )

        # Upsert: check for existing score
        existing = await db.execute(
            select(Score).where(
                Score.Judge_ID == judge.Judge_ID,
                Score.Project_ID == project_id,
                Score.Criterion_ID == entry.Criterion_ID,
            )
        )
        score = existing.scalar_one_or_none()
        if score:
            score.Score_Value = entry.Score_Value
            score.Scored_At = scored_at
        else:
            db.add(
                Score(
                    Judge_ID=judge.Judge_ID,
                    Project_ID=project_id,
                    Criterion_ID=entry.Criterion_ID,
                    Score_Value=entry.Score_Value,
                    Scored_At=scored_at,
                )
            )

    await db.commit()

    feedback_saved = True
    feedback_text = body.feedback.strip() if body.feedback is not None else None

    # Save feedback separately so optional feedback issues never drop the scores.
    if body.feedback is not None:
        try:
            fb_existing = await db.execute(
                select(Feedback).where(
                    Feedback.Judge_ID == judge.Judge_ID,
                    Feedback.Project_ID == project_id,
                )
            )

            fb = fb_existing.scalar_one_or_none()
            if feedback_text:
                if fb:
                    fb.Feedback_Text = feedback_text
                else:
                    db.add(
                        Feedback(
                            Judge_ID=judge.Judge_ID,
                            Project_ID=project_id,
                            Feedback_Text=feedback_text,
                        )
                    )
            elif fb:
                await db.delete(fb)

            await db.commit()
        except OperationalError:
            feedback_saved = False
            await db.rollback()
            log.warning(
                "Feedback could not be saved for judge %s project %s",
                judge.Judge_ID,
                project_id,
                exc_info=True,
            )

    return {
        "status": "ok",
        "project_id": project_id,
        "feedback_saved": feedback_saved,
    }


@router.get("/my-scores")
async def my_scores(
    judge: Judge = Depends(get_current_judge),
    db: AsyncSession = Depends(get_db),
):
    """List all projects this judge has scored with totals."""
    score_result = await db.execute(
        select(Score).where(Score.Judge_ID == judge.Judge_ID)
    )
    scores = score_result.scalars().all()

    # Group by project
    by_project: dict[str, list] = {}
    for s in scores:
        by_project.setdefault(s.Project_ID, []).append(s.Score_Value)

    # Get project info
    project_ids = list(by_project.keys())
    if not project_ids:
        return []

    proj_result = await db.execute(
        select(Project).where(Project.Project_ID.in_(project_ids))
    )
    projects = {p.Project_ID: p for p in proj_result.scalars().all()}

    result = []
    for pid, values in by_project.items():
        p = projects.get(pid)
        if p:
            result.append(
                {
                    "Project_ID": pid,
                    "Project_Number": p.Project_Number,
                    "Project_Title": p.Project_Title,
                    "Category": p.Category,
                    "Total_Score": sum(values),
                    "Criteria_Scored": len(values),
                }
            )

    result.sort(key=lambda x: x["Project_Number"])
    return result
