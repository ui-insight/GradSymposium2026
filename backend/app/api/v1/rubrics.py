"""Rubric management routes (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.competition import CompetitionSettings
from app.models.rubric import Rubric
from app.models.rubric_criterion import RubricCriterion
from app.models.score import Score
from app.models.user import User
from app.schemas.rubric import (
    CriterionCreate,
    CriterionRead,
    CriterionUpdate,
    RubricCreate,
    RubricRead,
    RubricUpdate,
)
from app.services.competition import lock_event

router = APIRouter(prefix="/rubrics", tags=["rubrics"])


async def _has_scores(db, rubric):
    return bool(
        await db.scalar(
            select(func.count())
            .select_from(Score)
            .join(RubricCriterion, RubricCriterion.Criterion_ID == Score.Criterion_ID)
            .where(RubricCriterion.Rubric_ID == rubric.Rubric_ID)
        )
    )


async def _editable(db, rubric):
    await lock_event(db, rubric.Event_ID)
    await db.refresh(rubric)
    rules = await db.get(CompetitionSettings, rubric.Event_ID)
    if (
        rubric.Is_Locked
        or await _has_scores(db, rubric)
        or (rules and rules.Judging_Open)
    ):
        raise HTTPException(
            409,
            "Close judging and unlock an unscored rubric before editing. "
            "Scored rubrics are frozen.",
        )


async def _total(db, rubric):
    await db.flush()
    rubric.Max_Score = await db.scalar(
        select(func.coalesce(func.sum(RubricCriterion.Max_Score), 0)).where(
            RubricCriterion.Rubric_ID == rubric.Rubric_ID
        )
    )


@router.post("/", response_model=RubricRead, status_code=201)
async def create_rubric(
    body: RubricCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    await lock_event(db, body.Event_ID)
    if not body.Rubric_Name.strip():
        raise HTTPException(422, "Provide a rubric name")
    if await db.scalar(
        select(Rubric.Rubric_ID).where(
            Rubric.Event_ID == body.Event_ID, Rubric.Category == body.Category
        )
    ):
        raise HTTPException(409, "A rubric for this event/category already exists")
    rubric = Rubric(**body.model_dump(), Max_Score=0)
    db.add(rubric)
    await db.commit()
    await db.refresh(rubric)
    return rubric


@router.post("/{rubric_id}/lock", response_model=RubricRead)
async def lock_rubric(
    rubric_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rubric = await db.get(Rubric, rubric_id)
    if not rubric:
        raise HTTPException(404, "Rubric not found")
    await lock_event(db, rubric.Event_ID)
    await db.refresh(rubric)
    if not rubric.criteria:
        raise HTTPException(
            409, "Add the approved criteria before confirming this rubric"
        )
    rubric.Is_Locked = True
    await _total(db, rubric)
    await db.commit()
    await db.refresh(rubric)
    return rubric


@router.post("/{rubric_id}/unlock", response_model=RubricRead)
async def unlock_rubric(
    rubric_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    rubric = await db.get(Rubric, rubric_id)
    if not rubric:
        raise HTTPException(404, "Rubric not found")
    await lock_event(db, rubric.Event_ID)
    rules = await db.get(CompetitionSettings, rubric.Event_ID)
    if await _has_scores(db, rubric) or (rules and rules.Judging_Open):
        raise HTTPException(
            409,
            "Scored rubrics remain frozen; "
            "close judging before unlocking an unscored rubric",
        )
    rubric.Is_Locked = False
    await db.commit()
    await db.refresh(rubric)
    return rubric


@router.get("/", response_model=list[RubricRead])
async def list_rubrics(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(
        select(Rubric).where(Rubric.Event_ID == event_id).order_by(Rubric.Category)
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
    await _editable(db, rubric)
    for key, val in body.model_dump(exclude_unset=True).items():
        if key == "Rubric_Name" and (not val or not val.strip()):
            raise HTTPException(422, "Provide a rubric name")
        setattr(rubric, key, val)
    await db.commit()
    await db.refresh(rubric)
    return rubric


@router.post(
    "/{rubric_id}/criteria",
    response_model=CriterionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_criterion(
    rubric_id: str,
    body: CriterionCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_current_admin),
):
    result = await db.execute(select(Rubric).where(Rubric.Rubric_ID == rubric_id))
    rubric = result.scalar_one_or_none()
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric not found")
    await _editable(db, rubric)
    if len(rubric.criteria) >= 100:
        raise HTTPException(422, "A rubric supports at most 100 criteria")
    criterion = RubricCriterion(Rubric_ID=rubric_id, **body.model_dump())
    db.add(criterion)
    await _total(db, rubric)
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
    rubric = await db.get(Rubric, criterion.Rubric_ID)
    await _editable(db, rubric)
    merged = {
        field: getattr(criterion, field) for field in CriterionCreate.model_fields
    }
    merged.update(body.model_dump(exclude_unset=True))
    try:
        CriterionCreate.model_validate(merged)
    except ValueError as exc:
        raise HTTPException(
            422, "Invalid criterion name or score range (supported range 0–5)"
        ) from exc
    for key, val in body.model_dump(exclude_unset=True).items():
        setattr(criterion, key, val)
    await _total(db, rubric)
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
    rubric = await db.get(Rubric, criterion.Rubric_ID)
    await _editable(db, rubric)
    await db.delete(criterion)
    await _total(db, rubric)
    await db.commit()
