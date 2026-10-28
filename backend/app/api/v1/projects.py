"""Project management routes (admin only)."""

import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.ballot_selection import BallotSelection
from app.models.competition import CompetitionSettings
from app.models.event import Event
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_conflict import JudgeConflict
from app.models.mentor_review import MentorReview
from app.models.project import Project
from app.models.score import Score
from app.models.user import User
from app.models.voting_round import VotingRound
from app.schemas.project import (
    CSVImportResult,
    PosterPublication,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
)
from app.services.competition import lock_event
from app.services.csv_import import import_projects_from_csv
from app.services.project_numbering import lock_event_numbers, reserve_number

router = APIRouter(prefix="/projects", tags=["projects"])


def _project_to_read(project: Project, score_count: int = 0) -> ProjectRead:
    return ProjectRead(
        Project_ID=project.Project_ID,
        Event_ID=project.Event_ID,
        Project_Number=project.Project_Number,
        Project_Title=project.Project_Title,
        Presenter_First_Name=project.Presenter_First_Name,
        Presenter_Last_Name=project.Presenter_Last_Name,
        Presenter_Email=project.Presenter_Email,
        Presenter_Display_Name=project.Presenter_Display_Name,
        Institution=project.Institution,
        Judging_Eligible=project.Judging_Eligible,
        Voting_Eligible=project.Voting_Eligible,
        Award_Groups=project.Award_Groups,
        Is_Published=project.Is_Published,
        Roster_Review=project.Roster_Review,
        Roster_Review_Required=project.Roster_Review_Required,
        Department=project.Department,
        College=project.College,
        Advisor_Name=project.Advisor_Name,
        Category=project.Category,
        Table_Number=project.Table_Number,
        Is_Active=project.Is_Active,
        score_count=score_count,
    )


def _active_score_count(project: Project) -> int:
    return sum(1 for score in project.scores if score.Is_Active)


@router.get("/", response_model=list[ProjectRead])
async def list_projects(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    # Get projects with score counts
    stmt = (
        select(
            Project,
            func.count(Score.Score_ID.distinct()).label("sc"),
        )
        .outerjoin(
            Score,
            (Score.Project_ID == Project.Project_ID) & Score.Is_Active.is_(True),
        )
        .where(Project.Event_ID == event_id)
        .group_by(Project.Project_ID)
        .order_by(Project.Category, Project.Project_Number)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [_project_to_read(row[0], row[1]) for row in rows]


@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event_numbers(db, body.Event_ID)
    project_id = str(uuid.uuid4())
    try:
        number = await reserve_number(
            db, body.Event_ID, project_id, body.Category, body.Project_Number
        )
        project = Project(
            **body.model_dump(exclude={"Project_Number"}),
            Project_ID=project_id,
            Project_Number=number,
        )
        db.add(project)
        await db.commit()
    except (ValueError, IntegrityError) as exc:
        await db.rollback()
        detail = str(exc) if isinstance(exc, ValueError) else "Project number conflict"
        raise HTTPException(status_code=409, detail=detail) from exc
    await db.refresh(project)
    return _project_to_read(project)


@router.post("/import-csv", response_model=CSVImportResult)
async def import_csv(
    event_id: str,
    file: UploadFile,
    dry_run: bool = False,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    try:
        content = (await file.read()).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Upload a UTF-8 CSV file") from exc
    try:
        return await import_projects_from_csv(db, event_id, content, dry_run=dry_run)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Roster changed; preview the import again"
        ) from exc


@router.post("/publication")
async def publish_posters(
    body: PosterPublication,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event_numbers(db, body.Event_ID)
    event = await db.get(Event, body.Event_ID)
    active_events = list(
        await db.scalars(select(Event).where(Event.Is_Active.is_(True)))
    )
    if body.Is_Published and (
        len(active_events) != 1 or active_events[0].Event_ID != event.Event_ID
    ):
        raise HTTPException(
            status_code=409, detail="Activate exactly this event before publishing"
        )
    if body.Is_Published:
        review_count = await db.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.Event_ID == body.Event_ID,
                Project.Is_Active.is_(True),
                Project.Roster_Review_Required.is_(True),
            )
        )
        if review_count:
            raise HTTPException(
                status_code=409,
                detail=f"Review {review_count} submissions before publishing",
            )
    statement = update(Project).where(
        Project.Event_ID == body.Event_ID, Project.Category == "Poster"
    )
    if body.Is_Published:
        statement = statement.where(Project.Is_Active.is_(True))
    await db.execute(statement.values(Is_Published=body.Is_Published))
    event.Public_Poster_Lookup_Enabled = body.Is_Published
    await db.commit()
    return {"Is_Published": body.Is_Published}


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Project).where(Project.Project_ID == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_read(project, _active_score_count(project))


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Project).where(Project.Project_ID == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await lock_event(db, project.Event_ID)
    await db.refresh(project)
    if (
        "Project_Number" in body.model_fields_set
        and body.Project_Number != project.Project_Number
    ):
        raise HTTPException(
            status_code=409, detail="Issued poster numbers cannot be changed"
        )
    if "Category" in body.model_fields_set and body.Category != project.Category:
        raise HTTPException(
            status_code=409, detail="Numbered project categories cannot be changed"
        )
    rules = await db.get(CompetitionSettings, project.Event_ID)
    if (
        rules
        and rules.Judging_Open
        and any(
            getattr(body, key) != getattr(project, key)
            for key in body.model_fields_set & {"Judging_Eligible", "Award_Groups"}
        )
    ):
        raise HTTPException(
            409, "Close judging before changing eligibility or award groups"
        )
    if (
        "Voting_Eligible" in body.model_fields_set
        and body.Voting_Eligible != project.Voting_Eligible
        and await db.scalar(
            select(VotingRound.Round_ID).where(
                VotingRound.Event_ID == project.Event_ID, VotingRound.Status == "open"
            )
        )
    ):
        raise HTTPException(
            409,
            "Close voting rounds before changing voting eligibility; "
            "use withdrawal for a withdrawal",
        )
    required = {"Project_Title", "Presenter_First_Name", "Presenter_Last_Name"}
    if any(getattr(body, field) is None for field in body.model_fields_set & required):
        raise HTTPException(status_code=422, detail="Required fields cannot be null")
    merged = {key: getattr(project, key) for key in ProjectCreate.model_fields}
    merged.update(body.model_dump(exclude_unset=True))
    try:
        validated = ProjectCreate.model_validate(merged)
        if "Award_Groups" in body.model_fields_set:
            body.Award_Groups = validated.Award_Groups
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="Provide a title and presenter name"
        ) from exc
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(project, key, val)
    project.Is_Published = False
    await db.commit()
    await db.refresh(project)
    return _project_to_read(project, _active_score_count(project))


@router.post("/{project_id}/withdraw", response_model=ProjectRead)
async def withdraw_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Withdraw a project: deactivate it and clear its judge assignments."""
    result = await db.execute(select(Project).where(Project.Project_ID == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await lock_event(db, project.Event_ID)
    await db.refresh(project)
    if not project.Is_Active:
        raise HTTPException(status_code=400, detail="Project is already withdrawn")
    project.Is_Active = False
    project.Is_Published = False
    await db.execute(
        delete(JudgeAssignment).where(JudgeAssignment.Project_ID == project_id)
    )
    await db.commit()
    await db.refresh(project)
    return _project_to_read(project, _active_score_count(project))


@router.post("/{project_id}/approve-roster", response_model=ProjectRead)
async def approve_roster(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await lock_event_numbers(db, project.Event_ID)
    await db.refresh(project)
    if not project.Is_Active or not project.Roster_Review_Required:
        raise HTTPException(
            status_code=409, detail="Project is not awaiting an active roster decision"
        )
    project.Roster_Review = {
        **(project.Roster_Review or {}),
        "approved_by": admin.User_ID,
        "approved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    project.Roster_Review_Required = False
    project.Is_Published = False
    await db.commit()
    await db.refresh(project)
    return _project_to_read(project, _active_score_count(project))


@router.post("/{project_id}/reinstate", response_model=ProjectRead)
async def reinstate_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Reinstate a previously withdrawn project."""
    result = await db.execute(select(Project).where(Project.Project_ID == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await lock_event(db, project.Event_ID)
    await db.refresh(project)
    if project.Is_Active:
        raise HTTPException(status_code=400, detail="Project is already active")
    project.Is_Active = True
    project.Is_Published = False
    await db.commit()
    await db.refresh(project)
    return _project_to_read(project, _active_score_count(project))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Project).where(Project.Project_ID == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await lock_event(db, project.Event_ID)
    await db.refresh(project)
    await lock_event_numbers(db, project.Event_ID)
    if (
        await db.scalar(
            select(BallotSelection.Selection_ID).where(
                BallotSelection.Project_ID == project_id
            )
        )
        or await db.scalar(
            select(JudgeConflict.Conflict_ID).where(
                JudgeConflict.Project_ID == project_id
            )
        )
        or await db.scalar(
            select(MentorReview.Review_ID).where(MentorReview.Project_ID == project_id)
        )
        or project.scores
    ):
        raise HTTPException(
            409, "Withdraw this presentation to preserve competition history"
        )
    await db.execute(
        delete(JudgeAssignment).where(JudgeAssignment.Project_ID == project_id)
    )
    await db.delete(project)
    await db.commit()
