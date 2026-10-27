"""Shared competition checks and complete-review accounting."""

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.models.competition import CompetitionSettings
from app.models.event import Event
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_conflict import JudgeConflict
from app.models.project import Project
from app.models.rubric import Rubric
from app.models.score import Score


async def lock_event(db: AsyncSession, event_id: str) -> None:
    result = await db.execute(
        update(Event)
        .where(Event.Event_ID == event_id)
        .values(Is_Active=Event.Is_Active)
    )
    if result.rowcount != 1:
        raise HTTPException(404, "Event not found")


async def has_conflict(db: AsyncSession, judge_id: str, project_id: str) -> bool:
    return bool(
        await db.scalar(
            select(JudgeConflict.Conflict_ID).where(
                JudgeConflict.Judge_ID == judge_id,
                JudgeConflict.Project_ID == project_id,
            )
        )
    )


async def validate_assignment(db: AsyncSession, judge_id: str, project_id: str):
    judge, project = (
        await db.get(Judge, judge_id, populate_existing=True),
        await db.get(Project, project_id, populate_existing=True),
    )
    if not judge or not project:
        raise HTTPException(404, "Judge or project not found")
    if judge.Event_ID != project.Event_ID:
        raise HTTPException(422, "Judge and project must belong to the same event")
    if not judge.Is_Active or not project.Is_Active:
        raise HTTPException(409, "Assign active judges to active projects only")
    rules = await db.get(CompetitionSettings, project.Event_ID)
    if rules and (
        project.Judging_Eligible is not True or project.Roster_Review_Required
    ):
        raise HTTPException(
            409, "Confirm roster inclusion and judging eligibility before assigning"
        )
    if await has_conflict(db, judge_id, project_id):
        raise HTTPException(
            409, "An organizer-recorded conflict blocks this assignment"
        )
    return judge, project


async def complete_reviews(db: AsyncSession, event_id: str) -> list[dict]:
    """Count exactly one full, valid rubric per active judge/project pair.

    Loading at most the event's ~40k scalar score rows also catches legacy partial
    and foreign-rubric rows without dialect-specific SQL aggregation tricks.
    """
    projects = {
        p.Project_ID: p
        for p in await db.scalars(
            select(Project).where(
                Project.Event_ID == event_id, Project.Is_Active.is_(True)
            )
        )
    }
    rubrics = {
        r.Category: r
        for r in await db.scalars(select(Rubric).where(Rubric.Event_ID == event_id))
    }
    judges = set(
        await db.scalars(
            select(Judge.Judge_ID).where(
                Judge.Event_ID == event_id, Judge.Is_Active.is_(True)
            )
        )
    )
    conflicts = set(
        (
            await db.execute(
                select(JudgeConflict.Judge_ID, JudgeConflict.Project_ID)
                .join(Project, Project.Project_ID == JudgeConflict.Project_ID)
                .where(Project.Event_ID == event_id)
            )
        ).all()
    )
    rows = await db.execute(
        select(
            Score.Judge_ID,
            Score.Project_ID,
            Score.Criterion_ID,
            Score.Score_Value,
            Score.Scored_At,
        )
        .join(Project, Project.Project_ID == Score.Project_ID)
        .where(Project.Event_ID == event_id, Score.Is_Active.is_(True))
    )
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.Judge_ID, row.Project_ID)].append(row)
    reviews = []
    for (judge_id, project_id), scores in grouped.items():
        project = projects.get(project_id)
        rubric = rubrics.get(project.Category) if project else None
        if (
            not rubric
            or not rubric.criteria
            or judge_id not in judges
            or (judge_id, project_id) in conflicts
        ):
            continue
        expected = {c.Criterion_ID: c for c in rubric.criteria}
        if (
            len(scores) != len(expected)
            or {s.Criterion_ID for s in scores} != expected.keys()
        ):
            continue
        if any(
            not expected[s.Criterion_ID].Min_Score
            <= s.Score_Value
            <= expected[s.Criterion_ID].Max_Score
            for s in scores
        ):
            continue
        reviews.append(
            {
                "Judge_ID": judge_id,
                "Project_ID": project_id,
                "Total_Score": sum(s.Score_Value for s in scores),
                "Scored_At": max(s.Scored_At for s in scores),
            }
        )
    return reviews


async def competition_status(db: AsyncSession, event_id: str) -> dict:
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    rules = await db.get(CompetitionSettings, event_id)
    projects = list(
        await db.scalars(
            select(Project).where(
                Project.Event_ID == event_id, Project.Is_Active.is_(True)
            )
        )
    )
    rubrics = list(await db.scalars(select(Rubric).where(Rubric.Event_ID == event_id)))
    judges = list(
        await db.scalars(
            select(Judge).where(Judge.Event_ID == event_id, Judge.Is_Active.is_(True))
        )
    )
    conflicts = set(
        (
            await db.execute(
                select(JudgeConflict.Judge_ID, JudgeConflict.Project_ID)
                .join(Project, Project.Project_ID == JudgeConflict.Project_ID)
                .where(Project.Event_ID == event_id)
            )
        ).all()
    )
    assignments = (
        await db.execute(
            select(JudgeAssignment.Judge_ID, JudgeAssignment.Project_ID)
            .join(Project, Project.Project_ID == JudgeAssignment.Project_ID)
            .join(Judge, Judge.Judge_ID == JudgeAssignment.Judge_ID)
            .where(
                Project.Event_ID == event_id,
                Judge.Event_ID == event_id,
                Judge.Is_Active.is_(True),
            )
        )
    ).all()
    assigned = defaultdict(set)
    for judge_id, project_id in assignments:
        if (judge_id, project_id) not in conflicts:
            assigned[project_id].add(judge_id)
    completed = defaultdict(set)
    for review in await complete_reviews(db, event_id):
        completed[review["Project_ID"]].add(review["Judge_ID"])
    target = rules.Required_Reviews if rules else None
    coverage = [
        {
            "Project_ID": p.Project_ID,
            "Project_Number": p.Project_Number,
            "Presenter_Display_Name": p.Presenter_Display_Name
            or f"{p.Presenter_First_Name} {p.Presenter_Last_Name}".strip(),
            "Project_Title": p.Project_Title,
            "Judging_Eligible": p.Judging_Eligible,
            "Award_Groups": p.Award_Groups or [],
            "Assigned_Judges": len(assigned[p.Project_ID]),
            "Complete_Reviews": len(completed[p.Project_ID]),
            "Required_Reviews": target,
            "Missing_Reviews": max(0, target - len(completed[p.Project_ID]))
            if target
            else None,
        }
        for p in sorted(projects, key=lambda p: p.Project_Number)
    ]
    missing = []
    if not event.Is_Active and not (
        rules and rules.Is_Rehearsal and app_settings.dev_mode
    ):
        missing.append("An active event (or synthetic dev rehearsal)")
    if not rules or not rules.Rules_Confirmed:
        missing.append("Organizer confirmation of judging rules")
    for field, label in (
        ("Required_Reviews", "Required reviews per poster"),
        ("Assignment_Only", "Whether judges must be assigned"),
        ("Aggregation", "Score aggregation method"),
        ("Tie_Policy", "Tie policy"),
        ("Award_Groups", "Award groups (or explicitly none)"),
    ):
        if not rules or getattr(rules, field) is None:
            missing.append(label)
    unresolved = sum(p.Roster_Review_Required for p in projects)
    pending = sum(p.Judging_Eligible is None for p in projects)
    eligible = [p for p in projects if p.Judging_Eligible is True]
    if unresolved:
        missing.append(f"Roster decisions for {unresolved} active submissions")
    if pending:
        missing.append(f"Judging eligibility for {pending} active presentations")
    if not eligible:
        missing.append("At least one confirmed eligible presentation")
    categories = {p.Category for p in eligible}
    for category in categories:
        rubric = next((r for r in rubrics if r.Category == category), None)
        if not rubric or not rubric.criteria or not rubric.Is_Locked:
            missing.append(f"Confirmed and locked {category} rubric")
    if not judges:
        missing.append("Judge roster")
    if target and len(judges) < target:
        missing.append("Enough active judges for the review target")
    if rules and rules.Award_Groups:
        allowed = set(rules.Award_Groups)
        if any(
            not p.Award_Groups or not set(p.Award_Groups) <= allowed for p in eligible
        ):
            missing.append("Valid award-group membership for eligible presentations")
    if (
        rules
        and rules.Assignment_Only
        and target
        and any(len(assigned[p.Project_ID]) < target for p in eligible)
    ):
        missing.append(
            "Enough non-conflicted assignments for every eligible presentation"
        )
    return {
        "Event_ID": event_id,
        "Event_Name": event.Event_Name,
        "Is_Rehearsal": bool(rules and rules.Is_Rehearsal),
        "settings": {
            "Event_ID": event_id,
            "Required_Reviews": target,
            "Assignment_Only": rules.Assignment_Only if rules else None,
            "Aggregation": rules.Aggregation if rules else None,
            "Tie_Policy": rules.Tie_Policy if rules else None,
            "Award_Groups": rules.Award_Groups if rules else None,
            "Rules_Confirmed": rules.Rules_Confirmed if rules else False,
            "Judging_Open": rules.Judging_Open if rules else False,
        },
        "missing": missing,
        "coverage": coverage,
        "Active_Judges": len(judges),
        "Eligible_Projects": len(eligible),
        "Complete_Reviews": sum(
            len(completed[p.Project_ID])
            for p in eligible
            if not p.Roster_Review_Required
        ),
        "Projects_At_Target": sum(
            p.Judging_Eligible is True
            and target is not None
            and len(completed[p.Project_ID]) >= target
            for p in projects
        ),
    }


async def validate_submission(
    db: AsyncSession, judge: Judge, project: Project, entries
) -> Rubric:
    rules = await db.get(CompetitionSettings, project.Event_ID)
    event = await db.get(Event, project.Event_ID)
    if not event.Is_Active and not (
        rules and rules.Is_Rehearsal and app_settings.dev_mode
    ):
        raise HTTPException(409, "This event is archived; scoring is closed")
    rubric = await db.scalar(
        select(Rubric).where(
            Rubric.Event_ID == project.Event_ID, Rubric.Category == project.Category
        )
    )
    if not rubric or not rubric.criteria:
        raise HTTPException(409, "No rubric is configured for this presentation")
    if rules:
        if not rules.Judging_Open or not rules.Rules_Confirmed or not rubric.Is_Locked:
            raise HTTPException(
                409, "Judging is closed while competition rules are being prepared"
            )
        if project.Judging_Eligible is not True or project.Roster_Review_Required:
            raise HTTPException(409, "Presentation eligibility has not been confirmed")
        if rules.Assignment_Only and not await db.scalar(
            select(JudgeAssignment.Assignment_ID).where(
                JudgeAssignment.Judge_ID == judge.Judge_ID,
                JudgeAssignment.Project_ID == project.Project_ID,
            )
        ):
            raise HTTPException(403, "This presentation is not assigned to you")
    if await has_conflict(db, judge.Judge_ID, project.Project_ID):
        raise HTTPException(403, "A recorded conflict prevents this review")
    expected = {c.Criterion_ID: c for c in rubric.criteria}
    identifiers = [entry.Criterion_ID for entry in entries]
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != expected.keys():
        raise HTTPException(
            422, "Submit every criterion in this presentation's rubric exactly once"
        )
    if any(
        not expected[e.Criterion_ID].Min_Score
        <= e.Score_Value
        <= expected[e.Criterion_ID].Max_Score
        for e in entries
    ):
        raise HTTPException(422, "A score is outside its criterion's allowed range")
    return rubric
