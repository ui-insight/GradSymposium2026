"""Competition readiness, rules, review coverage, and explicit judge conflicts."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.competition import CompetitionSettings
from app.models.event import Event
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_conflict import JudgeConflict
from app.models.project import Project
from app.models.score import Score
from app.models.user import User
from app.schemas.competition import CompetitionUpdate, ConflictCreate
from app.services.competition import competition_status, lock_event

router = APIRouter(prefix="/competition", tags=["competition"])


@router.get("/rehearsals/list")
async def list_rehearsals(
    db: AsyncSession = Depends(get_db), _admin: User = Depends(get_current_admin)
):
    rows = await db.execute(
        select(Event.Event_ID, Event.Event_Name)
        .join(CompetitionSettings, CompetitionSettings.Event_ID == Event.Event_ID)
        .where(CompetitionSettings.Is_Rehearsal.is_(True))
    )
    return [{"Event_ID": event_id, "Event_Name": name} for event_id, name in rows]


@router.get("/{event_id}")
async def status(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    return await competition_status(db, event_id)


@router.put("/{event_id}/settings")
async def save_settings(
    event_id: str,
    body: CompetitionUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, event_id)
    rules = await db.get(CompetitionSettings, event_id)
    if rules and rules.Judging_Open:
        raise HTTPException(409, "Close judging before editing rules")
    scored = await db.scalar(
        select(func.count())
        .select_from(Score)
        .join(Project, Project.Project_ID == Score.Project_ID)
        .where(Project.Event_ID == event_id)
    )
    incoming = body.model_dump()
    if scored and (
        not rules
        or any(getattr(rules, key) != value for key, value in incoming.items())
    ):
        raise HTTPException(
            409,
            "Rules are frozen after the first score; "
            "preserve this event's audit history",
        )
    if not rules:
        rules = CompetitionSettings(Event_ID=event_id)
        db.add(rules)
    for key, value in incoming.items():
        setattr(rules, key, value)
    await db.commit()
    return await competition_status(db, event_id)


@router.post("/{event_id}/open")
async def open_judging(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, event_id)
    state = await competition_status(db, event_id)
    if state["missing"]:
        raise HTTPException(409, "Judging is not ready: " + "; ".join(state["missing"]))
    rules = await db.get(CompetitionSettings, event_id)
    rules.Judging_Open = True
    await db.commit()
    return await competition_status(db, event_id)


@router.post("/{event_id}/close")
async def close_judging(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, event_id)
    rules = await db.get(CompetitionSettings, event_id)
    if not rules:
        rules = CompetitionSettings(Event_ID=event_id)
        db.add(rules)
    rules.Judging_Open = False
    await db.commit()
    return await competition_status(db, event_id)


@router.get("/{event_id}/conflicts")
async def list_conflicts(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rows = await db.execute(
        select(JudgeConflict, Judge.First_Name, Judge.Last_Name, Project.Project_Number)
        .join(Judge, Judge.Judge_ID == JudgeConflict.Judge_ID)
        .join(Project, Project.Project_ID == JudgeConflict.Project_ID)
        .where(Project.Event_ID == event_id)
    )
    return [
        {
            "Conflict_ID": conflict.Conflict_ID,
            "Judge_ID": conflict.Judge_ID,
            "Project_ID": conflict.Project_ID,
            "Reason": conflict.Reason,
            "Judge_Name": f"{first} {last}",
            "Project_Number": number,
        }
        for conflict, first, last, number in rows
    ]


@router.post("/{event_id}/conflicts", status_code=201)
async def create_conflict(
    event_id: str,
    body: ConflictCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, event_id)
    judge, project = (
        await db.get(Judge, body.Judge_ID),
        await db.get(Project, body.Project_ID),
    )
    if (
        not judge
        or not project
        or judge.Event_ID != event_id
        or project.Event_ID != event_id
    ):
        raise HTTPException(422, "Judge and project must belong to this event")
    if not body.Reason.strip():
        raise HTTPException(422, "Provide the conflict reason")
    existing = await db.scalar(
        select(JudgeConflict).where(
            JudgeConflict.Judge_ID == body.Judge_ID,
            JudgeConflict.Project_ID == body.Project_ID,
        )
    )
    if existing:
        existing.Reason = body.Reason.strip()
    else:
        db.add(JudgeConflict(**body.model_dump()))
    await db.execute(
        delete(JudgeAssignment).where(
            JudgeAssignment.Judge_ID == body.Judge_ID,
            JudgeAssignment.Project_ID == body.Project_ID,
        )
    )
    await db.commit()
    return {
        "status": "recorded",
        "detail": (
            "Assignment removed. Historical scores are retained and excluded "
            "while the conflict exists."
        ),
    }


@router.delete("/{event_id}/conflicts/{conflict_id}", status_code=204)
async def delete_conflict(
    event_id: str,
    conflict_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, event_id)
    conflict = await db.get(JudgeConflict, conflict_id)
    project = await db.get(Project, conflict.Project_ID) if conflict else None
    if not conflict or not project or project.Event_ID != event_id:
        raise HTTPException(404, "Conflict not found in this event")
    await db.delete(conflict)
    await db.commit()
