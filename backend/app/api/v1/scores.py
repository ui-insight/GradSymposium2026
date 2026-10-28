"""Score viewing/management routes (admin only)."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.feedback import Feedback
from app.models.judge import Judge
from app.models.project import Project
from app.models.rubric_criterion import RubricCriterion
from app.models.score import Score
from app.models.score_override import ScoreOverride
from app.models.user import User
from app.schemas.score import (
    JudgeScoreReview,
    ProjectScoreReview,
    ProjectScoreReviewCriterion,
    ScoreOverrideRead,
    ScoreOverrideUpdate,
    ScoreRead,
)
from app.services.competition import lock_event

router = APIRouter(prefix="/scores", tags=["scores"])
log = logging.getLogger(__name__)


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
        .where(Project.Event_ID == event_id, Score.Is_Active.is_(True))
    )
    if judge_id:
        stmt = stmt.where(Score.Judge_ID == judge_id)
    if project_id:
        stmt = stmt.where(Score.Project_ID == project_id)
    stmt = stmt.order_by(Score.Scored_At.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/review/{project_id}", response_model=ProjectScoreReview)
async def get_project_score_review(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    project_result = await db.execute(
        select(Project).where(Project.Project_ID == project_id)
    )
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    score_rows = await db.execute(
        select(Score, Judge, RubricCriterion)
        .join(Judge, Score.Judge_ID == Judge.Judge_ID)
        .join(RubricCriterion, Score.Criterion_ID == RubricCriterion.Criterion_ID)
        .where(Score.Project_ID == project_id, Score.Is_Active.is_(True))
        .order_by(
            Judge.Last_Name,
            Judge.First_Name,
            RubricCriterion.Sort_Order,
            RubricCriterion.Criterion_ID,
        )
    )
    rows = score_rows.all()

    feedback_by_judge: dict[str, str] = {}
    try:
        feedback_rows = await db.execute(
            select(Feedback).where(
                Feedback.Project_ID == project_id,
                Feedback.Is_Active.is_(True),
            )
        )
        feedback_by_judge = {
            feedback.Judge_ID: feedback.Feedback_Text
            for feedback in feedback_rows.scalars().all()
        }
    except OperationalError:
        log.warning(
            "Feedback could not be loaded for score review project %s",
            project_id,
            exc_info=True,
        )

    score_ids = [score.Score_ID for score, _, _ in rows]
    overrides_by_score: dict[int, list[ScoreOverrideRead]] = {}
    if score_ids:
        override_rows = await db.execute(
            select(ScoreOverride, User.Username)
            .join(User, ScoreOverride.Admin_User_ID == User.User_ID)
            .where(ScoreOverride.Score_ID.in_(score_ids))
            .order_by(
                ScoreOverride.Overridden_At.asc(), ScoreOverride.Override_ID.asc()
            )
        )
        for override, username in override_rows.all():
            overrides_by_score.setdefault(override.Score_ID, []).append(
                ScoreOverrideRead(
                    Override_ID=override.Override_ID,
                    Old_Score_Value=override.Old_Score_Value,
                    New_Score_Value=override.New_Score_Value,
                    Admin_Username=username,
                    Overridden_At=override.Overridden_At,
                )
            )

    submissions: dict[str, JudgeScoreReview] = {}
    for score, judge, criterion in rows:
        judge_name = f"{judge.First_Name} {judge.Last_Name}"
        submission = submissions.get(judge.Judge_ID)
        if submission is None:
            submission = JudgeScoreReview(
                Judge_ID=judge.Judge_ID,
                Judge_Name=judge_name,
                Judge_Department=judge.Department,
                Submitted_At=score.Scored_At,
                Total_Score=0,
                Feedback_Text=feedback_by_judge.get(judge.Judge_ID),
                criteria=[],
            )
            submissions[judge.Judge_ID] = submission

        submission.Total_Score += score.Score_Value
        if submission.Submitted_At is None or score.Scored_At > submission.Submitted_At:
            submission.Submitted_At = score.Scored_At

        override_history = overrides_by_score.get(score.Score_ID, [])
        submission.criteria.append(
            ProjectScoreReviewCriterion(
                Score_ID=score.Score_ID,
                Criterion_ID=criterion.Criterion_ID,
                Criterion_Name=criterion.Criterion_Name,
                Criterion_Group=criterion.Criterion_Group,
                Min_Score=criterion.Min_Score,
                Max_Score=criterion.Max_Score,
                Score_Value=score.Score_Value,
                Original_Score_Value=(
                    override_history[0].Old_Score_Value
                    if override_history
                    else score.Score_Value
                ),
                Override_Count=len(override_history),
                Latest_Override=override_history[-1] if override_history else None,
            )
        )

    return ProjectScoreReview(
        Project_ID=project.Project_ID,
        Project_Number=project.Project_Number,
        Project_Title=project.Project_Title,
        Presenter_First_Name=project.Presenter_First_Name,
        Presenter_Last_Name=project.Presenter_Last_Name,
        Presenter_Display_Name=project.Presenter_Display_Name,
        Department=project.Department,
        Category=project.Category,
        submissions=list(submissions.values()),
    )


@router.patch("/{score_id}", response_model=ScoreRead)
async def override_score(
    score_id: int,
    body: ScoreOverrideUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Score).where(Score.Score_ID == score_id))
    score = result.scalar_one_or_none()
    if not score or not score.Is_Active:
        raise HTTPException(status_code=404, detail="Score not found")
    project = await db.get(Project, score.Project_ID)
    await lock_event(db, project.Event_ID)
    await db.refresh(score)
    if not score.Is_Active:
        raise HTTPException(404, "Score not found")
    criterion = await db.get(RubricCriterion, score.Criterion_ID)
    if not criterion.Min_Score <= body.Score_Value <= criterion.Max_Score:
        raise HTTPException(422, "Score is outside this criterion's allowed range")

    if score.Score_Value != body.Score_Value:
        db.add(
            ScoreOverride(
                Score_ID=score.Score_ID,
                Admin_User_ID=admin.User_ID,
                Old_Score_Value=score.Score_Value,
                New_Score_Value=body.Score_Value,
            )
        )
        score.Score_Value = body.Score_Value
        await db.commit()
        await db.refresh(score)

    return score


@router.delete(
    "/submissions/{project_id}/{judge_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_submission(
    project_id: str,
    judge_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    await lock_event(db, project.Event_ID)
    score_ids_result = await db.execute(
        select(Score).where(
            Score.Project_ID == project_id,
            Score.Judge_ID == judge_id,
        )
    )
    scores = score_ids_result.scalars().all()

    feedback_result = await db.execute(
        select(Feedback).where(
            Feedback.Project_ID == project_id,
            Feedback.Judge_ID == judge_id,
        )
    )
    feedback = feedback_result.scalar_one_or_none()

    has_active_scores = any(score.Is_Active for score in scores)
    has_active_feedback = feedback is not None and feedback.Is_Active
    if not has_active_scores and not has_active_feedback:
        raise HTTPException(status_code=404, detail="Submission not found")

    for score in scores:
        if score.Is_Active:
            score.Is_Active = False

    if feedback is not None and feedback.Is_Active:
        feedback.Is_Active = False

    await db.commit()


@router.delete("/{score_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_score(
    score_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Score).where(Score.Score_ID == score_id))
    score = result.scalar_one_or_none()
    if not score or not score.Is_Active:
        raise HTTPException(status_code=404, detail="Score not found")
    project = await db.get(Project, score.Project_ID)
    await lock_event(db, project.Event_ID)
    await db.refresh(score)
    score.Is_Active = False
    await db.commit()
