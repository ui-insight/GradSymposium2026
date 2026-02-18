"""Results aggregation service."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.judge import Judge
from app.models.project import Project
from app.models.score import Score
from app.schemas.results import EventSummary, ProjectResult


async def get_project_results(
    db: AsyncSession,
    event_id: str,
    category: str | None = None,
) -> list[ProjectResult]:
    """Get aggregated, ranked results for projects in an event."""

    # Subquery: total score per judge per project
    judge_totals = (
        select(
            Score.Project_ID,
            Score.Judge_ID,
            func.sum(Score.Score_Value).label("judge_total"),
        )
        .group_by(Score.Project_ID, Score.Judge_ID)
        .subquery()
    )

    # Aggregate across judges
    stmt = (
        select(
            Project.Project_ID,
            Project.Project_Number,
            Project.Project_Title,
            Project.Presenter_First_Name,
            Project.Presenter_Last_Name,
            Project.Department,
            Project.Category,
            func.count(judge_totals.c.Judge_ID.distinct()).label("judge_count"),
            func.sum(judge_totals.c.judge_total).label("total_score"),
        )
        .join(judge_totals, judge_totals.c.Project_ID == Project.Project_ID)
        .where(Project.Event_ID == event_id)
        .where(Project.Is_Active.is_(True))
        .group_by(Project.Project_ID)
    )

    if category:
        stmt = stmt.where(Project.Category == category)

    stmt = stmt.order_by(
        Project.Category,
        func.sum(judge_totals.c.judge_total).desc(),
    )

    result = await db.execute(stmt)
    rows = result.all()

    results: list[ProjectResult] = []
    current_category = None
    rank = 0

    for row in rows:
        judge_count = row.judge_count or 0
        total_score = row.total_score or 0
        avg_score = total_score / judge_count if judge_count > 0 else 0.0

        if row.Category != current_category:
            current_category = row.Category
            rank = 1
        else:
            rank += 1

        results.append(
            ProjectResult(
                Project_ID=row.Project_ID,
                Project_Number=row.Project_Number,
                Project_Title=row.Project_Title,
                Presenter_First_Name=row.Presenter_First_Name,
                Presenter_Last_Name=row.Presenter_Last_Name,
                Department=row.Department,
                Category=row.Category,
                Judge_Count=judge_count,
                Total_Score=total_score,
                Average_Score=round(avg_score, 2),
                Rank=rank,
            )
        )

    return results


async def get_event_summary(db: AsyncSession, event_id: str) -> EventSummary:
    """Get high-level event scoring statistics."""

    # Total projects
    proj_result = await db.execute(
        select(func.count(Project.Project_ID)).where(
            Project.Event_ID == event_id, Project.Is_Active.is_(True)
        )
    )
    total_projects = proj_result.scalar() or 0

    # Category counts
    poster_result = await db.execute(
        select(func.count(Project.Project_ID)).where(
            Project.Event_ID == event_id,
            Project.Category == "Poster",
            Project.Is_Active.is_(True),
        )
    )
    poster_count = poster_result.scalar() or 0

    art_result = await db.execute(
        select(func.count(Project.Project_ID)).where(
            Project.Event_ID == event_id,
            Project.Category == "Art",
            Project.Is_Active.is_(True),
        )
    )
    art_count = art_result.scalar() or 0

    # Total judges
    judge_result = await db.execute(
        select(func.count(Judge.Judge_ID)).where(
            Judge.Event_ID == event_id, Judge.Is_Active.is_(True)
        )
    )
    total_judges = judge_result.scalar() or 0

    # Total score submissions (unique judge-project pairs)
    score_pairs = await db.execute(
        select(
            func.count(
                func.distinct(Score.Judge_ID.op("||")(Score.Project_ID))
            )
        )
        .join(Project, Score.Project_ID == Project.Project_ID)
        .where(Project.Event_ID == event_id)
    )
    total_scores = score_pairs.scalar() or 0

    # Projects that have at least one score
    scored_projects = await db.execute(
        select(func.count(Score.Project_ID.distinct()))
        .join(Project, Score.Project_ID == Project.Project_ID)
        .where(Project.Event_ID == event_id)
    )
    projects_with_scores = scored_projects.scalar() or 0

    coverage = (
        (projects_with_scores / total_projects * 100) if total_projects > 0 else 0.0
    )

    return EventSummary(
        Total_Projects=total_projects,
        Total_Judges=total_judges,
        Total_Scores_Submitted=total_scores,
        Projects_With_Scores=projects_with_scores,
        Scoring_Coverage_Percent=round(coverage, 1),
        Poster_Count=poster_count,
        Art_Count=art_count,
    )
