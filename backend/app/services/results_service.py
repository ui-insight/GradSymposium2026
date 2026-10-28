"""Complete-review results; award rules and eligibility are organizer decisions."""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.competition import CompetitionSettings
from app.models.judge import Judge
from app.models.project import Project
from app.schemas.results import EventSummary, ProjectResult
from app.services.competition import complete_reviews


async def get_project_results(
    db: AsyncSession,
    event_id: str,
    category: str | None = None,
    award_group: str | None = None,
) -> list[ProjectResult]:
    rules = await db.get(CompetitionSettings, event_id)
    projects = list(
        await db.scalars(
            select(Project).where(
                Project.Event_ID == event_id, Project.Is_Active.is_(True)
            )
        )
    )
    totals = defaultdict(list)
    for review in await complete_reviews(db, event_id):
        totals[review["Project_ID"]].append(review["Total_Score"])
    candidates = []
    for project in projects:
        if category and project.Category != category:
            continue
        if rules and (
            project.Judging_Eligible is not True or project.Roster_Review_Required
        ):
            continue
        if award_group and award_group not in (project.Award_Groups or []):
            continue
        values = totals[project.Project_ID]
        if not values:
            continue
        average = sum(values) / len(values)
        metric = sum(values) if rules and rules.Aggregation == "total" else average
        candidates.append((project, values, average, metric))
    candidates.sort(
        key=lambda row: (
            row[0].Category,
            -row[3],
            -sum(row[1]) if not rules else 0,
            row[0].Project_Number,
        )
    )
    results = []
    category_index = defaultdict(int)
    qualified_index = defaultdict(int)
    previous = {}
    ranks = {}
    for project, values, average, metric in candidates:
        category_index[project.Category] += 1
        meets = (
            len(values) >= rules.Required_Reviews
            if rules and rules.Required_Reviews
            else None
        )
        group_selected = not (rules and rules.Award_Groups) or bool(award_group)
        qualified = bool(
            rules
            and rules.Rules_Confirmed
            and rules.Aggregation
            and rules.Tie_Policy
            and meets
            and group_selected
        )
        tied = (
            sum(
                p.Category == project.Category
                and m == metric
                and (
                    not rules
                    or not rules.Required_Reviews
                    or len(v) >= rules.Required_Reviews
                )
                for p, v, _, m in candidates
            )
            > 1
        )
        rank = category_index[project.Category] if not rules else 0
        if qualified:
            qualified_index[project.Category] += 1
            if previous.get(project.Category) != metric:
                ranks[project.Category] = qualified_index[project.Category]
            rank = ranks[project.Category]
            previous[project.Category] = metric
        scope = [
            candidate
            for candidate in projects
            if candidate.Category == project.Category
            and candidate.Judging_Eligible is True
            and not candidate.Roster_Review_Required
            and (not award_group or award_group in (candidate.Award_Groups or []))
        ]
        all_targets_met = bool(
            rules
            and rules.Required_Reviews
            and scope
            and all(len(totals[p.Project_ID]) >= rules.Required_Reviews for p in scope)
        )
        unresolved_roster = any(
            candidate.Category == project.Category
            and (candidate.Judging_Eligible is None or candidate.Roster_Review_Required)
            for candidate in projects
        )
        provisional = bool(
            rules
            and (
                not qualified
                or rules.Judging_Open
                or not all_targets_met
                or unresolved_roster
                or (tied and rules.Tie_Policy == "manual")
            )
        )
        results.append(
            ProjectResult(
                Project_ID=project.Project_ID,
                Project_Number=project.Project_Number,
                Project_Title=project.Project_Title,
                Presenter_First_Name=project.Presenter_First_Name,
                Presenter_Last_Name=project.Presenter_Last_Name,
                Presenter_Display_Name=project.Presenter_Display_Name,
                Department=project.Department,
                Category=project.Category,
                Judge_Count=len(values),
                Total_Score=sum(values),
                Average_Score=round(average, 2),
                Rank=rank,
                Required_Reviews=rules.Required_Reviews if rules else None,
                Meets_Review_Target=meets,
                Award_Groups=project.Award_Groups or [],
                Tied=tied,
                Provisional=provisional,
            )
        )
    return results


async def get_event_summary(db: AsyncSession, event_id: str) -> EventSummary:
    rules = await db.get(CompetitionSettings, event_id)
    projects = list(
        await db.scalars(
            select(Project).where(
                Project.Event_ID == event_id, Project.Is_Active.is_(True)
            )
        )
    )
    judges = list(
        await db.scalars(
            select(Judge.Judge_ID).where(
                Judge.Event_ID == event_id, Judge.Is_Active.is_(True)
            )
        )
    )
    eligible = {
        p.Project_ID
        for p in projects
        if not rules or (p.Judging_Eligible is True and not p.Roster_Review_Required)
    }
    reviews = [
        r for r in await complete_reviews(db, event_id) if r["Project_ID"] in eligible
    ]
    scored = {r["Project_ID"] for r in reviews}
    at_target = 0
    if rules and rules.Required_Reviews:
        at_target = sum(
            sum(r["Project_ID"] == project_id for r in reviews)
            >= rules.Required_Reviews
            for project_id in eligible
        )
    return EventSummary(
        Total_Projects=len(projects),
        Total_Judges=len(judges),
        Total_Scores_Submitted=len(reviews),
        Projects_With_Scores=len(scored),
        Scoring_Coverage_Percent=round(len(scored) / len(eligible) * 100, 1)
        if eligible
        else 0,
        Poster_Count=sum(p.Category == "Poster" for p in projects),
        Art_Count=sum(p.Category == "Art" for p in projects),
        Eligible_Projects=len(eligible),
        Required_Reviews=rules.Required_Reviews if rules else None,
        Projects_At_Target=at_target,
        Judging_Open=rules.Judging_Open if rules else False,
    )
