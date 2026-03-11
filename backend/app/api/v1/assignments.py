"""Judge assignment routes (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.judge_assignment import JudgeAssignment
from app.models.project import Project
from app.models.user import User

router = APIRouter(prefix="/assignments", tags=["assignments"])


class AssignmentCreate(BaseModel):
    Judge_ID: str
    Project_ID: str


class AssignmentBulk(BaseModel):
    assignments: list[AssignmentCreate]


class AssignmentRead(BaseModel):
    Assignment_ID: int
    Judge_ID: str
    Project_ID: str
    Project_Number: str | None = None
    Project_Title: str | None = None

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[AssignmentRead])
async def list_assignments(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(JudgeAssignment)
        .join(Project, JudgeAssignment.Project_ID == Project.Project_ID)
        .where(Project.Event_ID == event_id)
    )
    assignments = result.scalars().all()
    return [
        AssignmentRead(
            Assignment_ID=a.Assignment_ID,
            Judge_ID=a.Judge_ID,
            Project_ID=a.Project_ID,
            Project_Number=a.project.Project_Number if a.project else None,
            Project_Title=a.project.Project_Title if a.project else None,
        )
        for a in assignments
    ]


@router.post("/", response_model=AssignmentRead, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    body: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    assignment = JudgeAssignment(Judge_ID=body.Judge_ID, Project_ID=body.Project_ID)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return AssignmentRead(
        Assignment_ID=assignment.Assignment_ID,
        Judge_ID=assignment.Judge_ID,
        Project_ID=assignment.Project_ID,
    )


@router.post("/bulk", response_model=list[AssignmentRead], status_code=status.HTTP_201_CREATED)
async def bulk_create_assignments(
    body: AssignmentBulk,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    created = []
    for a in body.assignments:
        assignment = JudgeAssignment(Judge_ID=a.Judge_ID, Project_ID=a.Project_ID)
        db.add(assignment)
        created.append(assignment)
    await db.commit()
    return [
        AssignmentRead(
            Assignment_ID=a.Assignment_ID,
            Judge_ID=a.Judge_ID,
            Project_ID=a.Project_ID,
        )
        for a in created
    ]


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_assignments(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Remove all assignments for an event."""
    result = await db.execute(
        select(JudgeAssignment)
        .join(Project, JudgeAssignment.Project_ID == Project.Project_ID)
        .where(Project.Event_ID == event_id)
    )
    assignments = result.scalars().all()
    for a in assignments:
        await db.delete(a)
    await db.commit()


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(JudgeAssignment).where(JudgeAssignment.Assignment_ID == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.delete(assignment)
    await db.commit()
