"""Judge management routes (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.judge import Judge
from app.models.user import User
from app.schemas.judge import (
    AccessCodeCard,
    JudgeBulkCreate,
    JudgeCreate,
    JudgeRead,
    JudgeUpdate,
)
from app.services.access_code import generate_access_code

router = APIRouter(prefix="/judges", tags=["judges"])


def _judge_to_read(judge: Judge) -> JudgeRead:
    # Count unique project-score pairs
    scored_projects = {s.Project_ID for s in judge.scores}
    assigned_projects = {a.Project_ID for a in judge.assignments}
    return JudgeRead(
        Judge_ID=judge.Judge_ID,
        Event_ID=judge.Event_ID,
        First_Name=judge.First_Name,
        Last_Name=judge.Last_Name,
        Email=judge.Email,
        Department=judge.Department,
        Access_Code=judge.Access_Code,
        Is_Active=judge.Is_Active,
        assignment_count=len(assigned_projects),
        score_count=len(scored_projects),
    )


async def _unique_code(db: AsyncSession) -> str:
    for _ in range(100):
        code = generate_access_code()
        existing = await db.execute(
            select(Judge).where(Judge.Access_Code == code)
        )
        if not existing.scalar_one_or_none():
            return code
    raise RuntimeError("Unable to generate unique access code")


@router.get("/access-codes", response_model=list[AccessCodeCard])
async def get_access_codes(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Judge)
        .where(Judge.Event_ID == event_id, Judge.Is_Active.is_(True))
        .order_by(Judge.Last_Name)
    )
    judges = result.scalars().all()
    return [
        AccessCodeCard(
            First_Name=j.First_Name,
            Last_Name=j.Last_Name,
            Access_Code=j.Access_Code,
        )
        for j in judges
    ]


@router.get("/", response_model=list[JudgeRead])
async def list_judges(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Judge)
        .where(Judge.Event_ID == event_id)
        .order_by(Judge.Last_Name)
    )
    return [_judge_to_read(j) for j in result.scalars().all()]


@router.post("/", response_model=JudgeRead, status_code=status.HTTP_201_CREATED)
async def create_judge(
    body: JudgeCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    code = await _unique_code(db)
    judge = Judge(
        Event_ID=body.Event_ID,
        First_Name=body.First_Name,
        Last_Name=body.Last_Name,
        Email=body.Email,
        Department=body.Department,
        Access_Code=code,
    )
    db.add(judge)
    await db.commit()
    await db.refresh(judge)
    return _judge_to_read(judge)


@router.post("/bulk", response_model=list[JudgeRead], status_code=status.HTTP_201_CREATED)
async def bulk_create_judges(
    body: JudgeBulkCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    created = []
    for j in body.judges:
        code = await _unique_code(db)
        judge = Judge(
            Event_ID=body.Event_ID,
            First_Name=j.First_Name,
            Last_Name=j.Last_Name,
            Email=j.Email,
            Department=j.Department,
            Access_Code=code,
        )
        db.add(judge)
        created.append(judge)
    await db.commit()
    for j in created:
        await db.refresh(j)
    return [_judge_to_read(j) for j in created]


@router.get("/{judge_id}", response_model=JudgeRead)
async def get_judge(
    judge_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Judge).where(Judge.Judge_ID == judge_id))
    judge = result.scalar_one_or_none()
    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")
    return _judge_to_read(judge)


@router.patch("/{judge_id}", response_model=JudgeRead)
async def update_judge(
    judge_id: str,
    body: JudgeUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Judge).where(Judge.Judge_ID == judge_id))
    judge = result.scalar_one_or_none()
    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(judge, key, val)
    await db.commit()
    await db.refresh(judge)
    return _judge_to_read(judge)


@router.delete("/{judge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_judge(
    judge_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Judge).where(Judge.Judge_ID == judge_id))
    judge = result.scalar_one_or_none()
    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")
    await db.delete(judge)
    await db.commit()


@router.post("/{judge_id}/regenerate-code", response_model=JudgeRead)
async def regenerate_code(
    judge_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Judge).where(Judge.Judge_ID == judge_id))
    judge = result.scalar_one_or_none()
    if not judge:
        raise HTTPException(status_code=404, detail="Judge not found")
    judge.Access_Code = await _unique_code(db)
    await db.commit()
    await db.refresh(judge)
    return _judge_to_read(judge)
