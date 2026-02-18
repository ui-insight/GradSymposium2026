"""Rubric management routes (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.rubric import Rubric
from app.models.rubric_criterion import RubricCriterion
from app.models.user import User
from app.schemas.rubric import (
    CriterionCreate,
    CriterionRead,
    CriterionUpdate,
    RubricRead,
    RubricUpdate,
)

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


@router.get("/", response_model=list[RubricRead])
async def list_rubrics(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Rubric)
        .where(Rubric.Event_ID == event_id)
        .order_by(Rubric.Category)
    )
    return result.scalars().all()


@router.get("/{rubric_id}", response_model=RubricRead)
async def get_rubric(
    rubric_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Rubric).where(Rubric.Rubric_ID == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    return rubric


@router.patch("/{rubric_id}", response_model=RubricRead)
async def update_rubric(
    rubric_id: str,
    body: RubricUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Rubric).where(Rubric.Rubric_ID == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(rubric, key, val)
    await db.commit()
    await db.refresh(rubric)
    return rubric


@router.post("/{rubric_id}/criteria", response_model=CriterionRead, status_code=status.HTTP_201_CREATED)
async def add_criterion(
    rubric_id: str,
    body: CriterionCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Rubric).where(Rubric.Rubric_ID == rubric_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Rubric not found")
    criterion = RubricCriterion(Rubric_ID=rubric_id, **body.model_dump())
    db.add(criterion)
    await db.commit()
    await db.refresh(criterion)
    return criterion


@router.patch("/criteria/{criterion_id}", response_model=CriterionRead)
async def update_criterion(
    criterion_id: int,
    body: CriterionUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(RubricCriterion).where(RubricCriterion.Criterion_ID == criterion_id)
    )
    criterion = result.scalar_one_or_none()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(criterion, key, val)
    await db.commit()
    await db.refresh(criterion)
    return criterion


@router.delete("/criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_criterion(
    criterion_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(RubricCriterion).where(RubricCriterion.Criterion_ID == criterion_id)
    )
    criterion = result.scalar_one_or_none()
    if not criterion:
        raise HTTPException(status_code=404, detail="Criterion not found")
    await db.delete(criterion)
    await db.commit()
