"""Paul's approved ASM rubric, installed only into an empty editable draft."""

from sqlalchemy import func, select

from app.models.competition import CompetitionSettings
from app.models.rubric import Rubric
from app.models.rubric_criterion import RubricCriterion
from app.models.score import Score
from app.services.competition import lock_event

NAME = "ASM poster rubric"
DESCRIPTION = "Score each criterion from 0 to 5. Maximum 20 points per review."
SCORE_LABELS = {
    "0": "Not demonstrated",
    "1": "Limited",
    "2": "Fair",
    "3": "Good",
    "4": "Very good",
    "5": "Excellent",
}
CRITERIA = (
    ("Research question", "Is the purpose of the research clear and important?"),
    ("Methods", "Are the methods appropriate and clearly explained?"),
    ("Results", "Are the results easy to understand and supported by evidence?"),
    (
        "Presentation",
        "Is the poster clear and organized? Does the presenter explain the work "
        "and answer questions?",
    ),
)


async def configure_asm_rubric(db, event_id):
    """Leave existing decisions/history alone; caller owns the transaction."""
    await lock_event(db, event_id)
    rubric = await db.scalar(
        select(Rubric).where(Rubric.Event_ID == event_id, Rubric.Category == "Poster")
    )
    if rubric:
        matches = (
            rubric.Rubric_Name == NAME
            and rubric.Description == DESCRIPTION
            and rubric.Score_Labels == SCORE_LABELS
            and rubric.Max_Score == 20
            and [
                (
                    c.Criterion_Name,
                    c.Description,
                    c.Min_Score,
                    c.Max_Score,
                    c.Sort_Order,
                )
                for c in rubric.criteria
            ]
            == [
                (name, guidance, 0, 5, i) for i, (name, guidance) in enumerate(CRITERIA)
            ]
        )
        if matches:
            return rubric
        has_scores = await db.scalar(
            select(func.count())
            .select_from(Score)
            .join(RubricCriterion)
            .where(RubricCriterion.Rubric_ID == rubric.Rubric_ID)
        )
        rules = await db.get(CompetitionSettings, event_id)
        if (
            rubric.criteria
            or rubric.Is_Locked
            or has_scores
            or (rules and rules.Judging_Open)
        ):
            raise RuntimeError(
                "ASM rubric differs from Paul's rubric and is edited, locked, "
                "scored or open for judging. Review it in admin; nothing was replaced."
            )
    else:
        rubric = Rubric(Event_ID=event_id, Category="Poster", Max_Score=0)
        db.add(rubric)
    rubric.Rubric_Name = NAME
    rubric.Description = DESCRIPTION
    rubric.Score_Labels = dict(SCORE_LABELS)
    rubric.Max_Score = sum(5 for _ in CRITERIA)
    rubric.criteria = [
        RubricCriterion(
            Criterion_Name=name,
            Description=guidance,
            Min_Score=0,
            Max_Score=5,
            Sort_Order=i,
        )
        for i, (name, guidance) in enumerate(CRITERIA)
    ]
    await db.flush()
    return rubric
