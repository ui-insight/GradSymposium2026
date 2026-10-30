"""Judge assignment routes (admin only)."""

import random

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.competition import CompetitionSettings
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_conflict import JudgeConflict
from app.models.project import Project
from app.models.user import User
from app.schemas.competition import AutoAssignmentCreate
from app.services.competition import (
    complete_reviews,
    lock_event,
    record_conflict,
    validate_assignment,
)

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
    project = await db.get(Project, body.Project_ID)
    if not project:
        raise HTTPException(404, "Project not found")
    await lock_event(db, project.Event_ID)
    await validate_assignment(db, body.Judge_ID, body.Project_ID)
    assignment = await db.scalar(
        select(JudgeAssignment).where(
            JudgeAssignment.Judge_ID == body.Judge_ID,
            JudgeAssignment.Project_ID == body.Project_ID,
        )
    )
    if assignment:
        return AssignmentRead.model_validate(assignment)
    assignment = JudgeAssignment(Judge_ID=body.Judge_ID, Project_ID=body.Project_ID)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return AssignmentRead(
        Assignment_ID=assignment.Assignment_ID,
        Judge_ID=assignment.Judge_ID,
        Project_ID=assignment.Project_ID,
    )


@router.post(
    "/bulk", response_model=list[AssignmentRead], status_code=status.HTTP_201_CREATED
)
async def bulk_create_assignments(
    body: AssignmentBulk,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    if not body.assignments:
        return []
    pairs = {(a.Judge_ID, a.Project_ID) for a in body.assignments}
    if len(pairs) != len(body.assignments):
        raise HTTPException(422, "Duplicate assignments in this request")
    project = await db.get(Project, body.assignments[0].Project_ID)
    if not project:
        raise HTTPException(404, "Project not found")
    await lock_event(db, project.Event_ID)
    for a in body.assignments:
        _, candidate = await validate_assignment(db, a.Judge_ID, a.Project_ID)
        if candidate.Event_ID != project.Event_ID:
            raise HTTPException(422, "Import assignments for one event at a time")
    created = []
    for a in body.assignments:
        existing = await db.scalar(
            select(JudgeAssignment).where(
                JudgeAssignment.Judge_ID == a.Judge_ID,
                JudgeAssignment.Project_ID == a.Project_ID,
            )
        )
        if existing:
            created.append(existing)
            continue
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


@router.post("/auto")
async def auto_assign(
    body: AutoAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, body.Event_ID)
    rules = await db.get(CompetitionSettings, body.Event_ID)
    target = body.Judges_Per_Project or (rules.Required_Reviews if rules else None)
    if not target:
        raise HTTPException(409, "Set a review target before distributing judges")
    projects = list(
        await db.scalars(
            select(Project).where(
                Project.Event_ID == body.Event_ID, Project.Is_Active.is_(True)
            )
        )
    )
    projects = [
        p
        for p in projects
        if (not body.Category or p.Category == body.Category)
        and (not rules or (p.Judging_Eligible is True and not p.Roster_Review_Required))
    ]
    judge_ids = list(
        await db.scalars(
            select(Judge.Judge_ID).where(
                Judge.Event_ID == body.Event_ID, Judge.Is_Active.is_(True)
            )
        )
    )
    current = (
        await db.execute(
            select(JudgeAssignment.Judge_ID, JudgeAssignment.Project_ID)
            .join(Project, Project.Project_ID == JudgeAssignment.Project_ID)
            .where(Project.Event_ID == body.Event_ID)
        )
    ).all()
    conflicts = set(
        (
            await db.execute(
                select(JudgeConflict.Judge_ID, JudgeConflict.Project_ID)
                .join(Project, Project.Project_ID == JudgeConflict.Project_ID)
                .where(Project.Event_ID == body.Event_ID)
            )
        ).all()
    )
    pairs = set(current)
    loads = {judge_id: sum(j == judge_id for j, _ in current) for judge_id in judge_ids}
    random.shuffle(projects)
    created, shortages = 0, []
    for project in projects:
        assigned = {
            j
            for j, p in pairs
            if p == project.Project_ID and j in loads and (j, p) not in conflicts
        }
        available = [
            j
            for j in judge_ids
            if j not in assigned and (j, project.Project_ID) not in conflicts
        ]
        random.shuffle(available)
        available.sort(key=lambda j: loads[j])
        for judge_id in available[: max(0, target - len(assigned))]:
            db.add(JudgeAssignment(Judge_ID=judge_id, Project_ID=project.Project_ID))
            pairs.add((judge_id, project.Project_ID))
            assigned.add(judge_id)
            loads[judge_id] += 1
            created += 1
        if len(assigned) < target:
            shortages.append(
                {
                    "Project_Number": project.Project_Number,
                    "Assigned": len(assigned),
                    "Target": target,
                }
            )
    await db.commit()
    return {
        "created": created,
        "eligible_projects": len(projects),
        "shortages": shortages,
    }


@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_assignments(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    """Remove all assignments for an event."""
    await lock_event(db, event_id)
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
    project = await db.get(Project, assignment.Project_ID)
    await lock_event(db, project.Event_ID)
    await db.delete(assignment)
    await db.commit()


class ConflictReplacement(BaseModel):
    Assignment_ID: int
    Judge_ID: str
    Project_ID: str
    Replacement_Judge_ID: str | None = None
    Reason: str = Field(min_length=1, max_length=500)


@router.post("/report-conflict")
async def replace_conflicted_assignment(
    body: ConflictReplacement,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    assignment = await db.get(JudgeAssignment, body.Assignment_ID)
    if not assignment:
        raise HTTPException(
            409, "Assignment changed. Refresh before reporting a conflict."
        )
    project = await db.get(Project, assignment.Project_ID)
    await lock_event(db, project.Event_ID)
    assignment = await db.get(
        JudgeAssignment, body.Assignment_ID, populate_existing=True
    )
    if not assignment:
        raise HTTPException(409, "Assignment changed. Refresh and try again.")
    if assignment.Judge_ID != body.Judge_ID or assignment.Project_ID != body.Project_ID:
        raise HTTPException(409, "Assignment changed. Refresh and try again.")
    if not body.Reason.strip():
        raise HTTPException(422, "Provide the conflict reason")
    if body.Replacement_Judge_ID:
        if body.Replacement_Judge_ID == assignment.Judge_ID:
            raise HTTPException(422, "Choose a different judge")
        await validate_assignment(db, body.Replacement_Judge_ID, project.Project_ID)
        existing = await db.scalar(
            select(JudgeAssignment).where(
                JudgeAssignment.Judge_ID == body.Replacement_Judge_ID,
                JudgeAssignment.Project_ID == project.Project_ID,
            )
        )
        if existing:
            raise HTTPException(
                409, "Replacement already assigned. Refresh and choose another judge."
            )
    await record_conflict(db, assignment.Judge_ID, project.Project_ID, body.Reason)
    if body.Replacement_Judge_ID:
        db.add(
            JudgeAssignment(
                Judge_ID=body.Replacement_Judge_ID, Project_ID=project.Project_ID
            )
        )
    await db.flush()
    assignments = list(
        await db.scalars(
            select(JudgeAssignment).where(
                JudgeAssignment.Project_ID == project.Project_ID
            )
        )
    )
    reviews = await complete_reviews(db, project.Event_ID)
    rules = await db.get(CompetitionSettings, project.Event_ID)
    result = {
        "assigned": len(assignments),
        "completed_reviews": sum(
            r["Project_ID"] == project.Project_ID for r in reviews
        ),
        "target": rules.Required_Reviews if rules else None,
    }
    await db.commit()
    return result
