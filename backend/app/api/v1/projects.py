"""Project management routes (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.judge_assignment import JudgeAssignment
from app.models.project import Project
from app.models.score import Score
from app.models.user import User
from app.schemas.project import CSVImportResult, ProjectCreate, ProjectRead, ProjectUpdate
from app.services.csv_import import import_projects_from_csv

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
        Department=project.Department,
        College=project.College,
        Advisor_Name=project.Advisor_Name,
        Category=project.Category,
        Table_Number=project.Table_Number,
        Is_Active=project.Is_Active,
        score_count=score_count,
    )


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
        .outerjoin(Score, Score.Project_ID == Project.Project_ID)
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
    project = Project(**body.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return _project_to_read(project)


@router.post("/import-csv", response_model=CSVImportResult)
async def import_csv(
    event_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    content = (await file.read()).decode("utf-8-sig")
    return await import_projects_from_csv(db, event_id, content)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Project).where(Project.Project_ID == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_read(project, len(project.scores))


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Project).where(Project.Project_ID == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(project, key, val)
    await db.commit()
    await db.refresh(project)
    return _project_to_read(project, len(project.scores))


@router.post("/{project_id}/withdraw", response_model=ProjectRead)
async def withdraw_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Withdraw a project: deactivate it and clear its judge assignments."""
    result = await db.execute(
        select(Project).where(Project.Project_ID == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.Is_Active:
        raise HTTPException(status_code=400, detail="Project is already withdrawn")
    project.Is_Active = False
    await db.execute(
        delete(JudgeAssignment).where(JudgeAssignment.Project_ID == project_id)
    )
    await db.commit()
    await db.refresh(project)
    return _project_to_read(project, len(project.scores))


@router.post("/{project_id}/reinstate", response_model=ProjectRead)
async def reinstate_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Reinstate a previously withdrawn project."""
    result = await db.execute(
        select(Project).where(Project.Project_ID == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.Is_Active:
        raise HTTPException(status_code=400, detail="Project is already active")
    project.Is_Active = True
    await db.commit()
    await db.refresh(project)
    return _project_to_read(project, len(project.scores))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Project).where(Project.Project_ID == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
