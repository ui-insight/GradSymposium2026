"""Current organizer evidence, stale-review detection and assignment warnings."""

import datetime
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import select

from app.models.event import Event
from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_conflict import JudgeConflict
from app.models.mentor_review import MentorReview
from app.models.project import Project
from app.models.score import Score
from app.services.competition import competition_status, record_conflict


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def source_context(judge, project):
    return digest(
        [
            judge.Judge_ID,
            judge.First_Name,
            judge.Last_Name,
            project.Project_ID,
            project.Project_Title,
            project.Presenter_First_Name,
            project.Presenter_Last_Name,
            project.Presenter_Display_Name,
            project.Advisor_Name,
            project.Institution,
            project.Is_Active,
            project.Judging_Eligible,
            project.Roster_Review_Required,
        ]
    )


async def apply_decision(db, judge_id, project_id, decision, note, reviewer):
    """Caller holds the event lock and validates the current review context."""
    source = source_context(
        await db.get(Judge, judge_id), await db.get(Project, project_id)
    )
    if decision == "conflict":
        await record_conflict(db, judge_id, project_id, note)
    review = await db.scalar(
        select(MentorReview).where(
            MentorReview.Judge_ID == judge_id, MentorReview.Project_ID == project_id
        )
    )
    if not review:
        review = MentorReview(Judge_ID=judge_id, Project_ID=project_id)
        db.add(review)
    review.Decision = decision
    review.Note = note
    review.Source_Context = source
    review.Reviewed_By = reviewer
    review.Reviewed_At = datetime.datetime.now(datetime.timezone.utc).replace(
        tzinfo=None
    )
    await db.flush()


async def review_workspace(db, event_id, judge_id=None, include_coverage=True):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    judges = list(
        await db.scalars(
            select(Judge)
            .where(Judge.Event_ID == event_id)
            .order_by(Judge.Last_Name, Judge.First_Name, Judge.Judge_ID)
        )
    )
    judge = next((j for j in judges if j.Judge_ID == judge_id), None)
    if judge_id and not judge:
        raise HTTPException(404, "Judge not found in this event")
    if not judge_id:
        judge = next((j for j in judges if j.Is_Active), None)
    projects = list(
        await db.scalars(
            select(Project)
            .where(Project.Event_ID == event_id)
            .order_by(Project.Project_Number)
        )
    )
    reviews, conflicts, assigned, scored = {}, {}, set(), set()
    if judge:
        reviews = {
            r.Project_ID: r
            for r in await db.scalars(
                select(MentorReview).where(MentorReview.Judge_ID == judge.Judge_ID)
            )
        }
        conflicts = {
            c.Project_ID: c
            for c in await db.scalars(
                select(JudgeConflict).where(JudgeConflict.Judge_ID == judge.Judge_ID)
            )
        }
        assigned = set(
            await db.scalars(
                select(JudgeAssignment.Project_ID).where(
                    JudgeAssignment.Judge_ID == judge.Judge_ID
                )
            )
        )
        scored = set(
            await db.scalars(
                select(Score.Project_ID).where(
                    Score.Judge_ID == judge.Judge_ID, Score.Is_Active.is_(True)
                )
            )
        )
    rows = []
    for project in projects if judge else []:
        review, conflict = (
            reviews.get(project.Project_ID),
            conflicts.get(project.Project_ID),
        )
        source = source_context(judge, project)
        if review and review.Source_Context != source:
            status = "stale"
        elif review and review.Decision == "needs_input":
            status = "needs_input"
        elif conflict:
            status = "conflict"
        elif review and review.Decision == "clear":
            status = "clear"
        else:
            status = "unreviewed"
        rows.append(
            {
                "Project_ID": project.Project_ID,
                "Project_Number": project.Project_Number,
                "Project_Title": project.Project_Title,
                "Presenter_Name": project.Presenter_Display_Name
                or f"{project.Presenter_First_Name} {project.Presenter_Last_Name}",
                "Advisor_Name": project.Advisor_Name,
                "Institution": project.Institution,
                "Is_Active": project.Is_Active,
                "Judging_Eligible": project.Judging_Eligible,
                "Roster_Review_Required": project.Roster_Review_Required,
                "Required": project.Is_Active
                and project.Judging_Eligible is True
                and not project.Roster_Review_Required,
                "Assigned": project.Project_ID in assigned,
                "Has_Scores": project.Project_ID in scored,
                "Status": status,
                "Note": review.Note if review else "",
                "Reviewed_By": review.Reviewed_By if review else None,
                "Reviewed_At": review.Reviewed_At if review else None,
                "Conflict_ID": conflict.Conflict_ID if conflict else None,
                "Conflict_Reason": conflict.Reason if conflict else None,
                "Context": digest(
                    [
                        source,
                        review.Reviewed_At if review else None,
                        review.Decision if review else None,
                        review.Note if review else None,
                        conflict.Conflict_ID if conflict else None,
                        conflict.Reason if conflict else None,
                        project.Project_ID in assigned,
                    ]
                ),
            }
        )
    required = [r for r in rows if r["Required"]]
    remaining = sum(r["Status"] not in {"clear", "conflict"} for r in required)
    unresolved_roster = sum(
        p.Is_Active and (p.Roster_Review_Required or p.Judging_Eligible is None)
        for p in projects
    )
    assignment_issues = sum(
        r["Assigned"] and (not r["Required"] or r["Conflict_ID"] is not None)
        for r in rows
    )
    blockers = []
    if not judge or not judge.Is_Active:
        blockers.append("Select an active judge")
    if unresolved_roster:
        blockers.append(
            f"Resolve roster/eligibility decisions for {unresolved_roster} "
            "presentations"
        )
    if not required:
        blockers.append("Confirm at least one eligible presentation")
    if remaining:
        blockers.append(f"Review {remaining} eligible judge/presentation relationships")
    if assignment_issues:
        blockers.append(
            f"Resolve {assignment_issues} excluded or conflicted assignments"
        )
    coverage = (
        await competition_status(db, event_id)
        if include_coverage
        else {"settings": {"Required_Reviews": None}, "coverage": []}
    )
    target = coverage["settings"]["Required_Reviews"]
    return {
        "Event_ID": event_id,
        "Event_Name": event.Event_Name,
        "Judges": [
            {
                "Judge_ID": j.Judge_ID,
                "Name": f"{j.First_Name} {j.Last_Name}",
                "Department": j.Department,
                "Is_Active": j.Is_Active,
                "Conflict_Review_Required": j.Conflict_Review_Required,
                "Previous_Name": j.Previous_Name,
            }
            for j in judges
        ],
        "Judge_ID": judge.Judge_ID if judge else None,
        "Projects": rows,
        "Remaining": remaining,
        "Completion_Blockers": blockers,
        "Context": digest(
            [
                [(r["Project_ID"], r["Context"]) for r in rows],
                judge.Is_Active if judge else None,
                judge.Conflict_Review_Required if judge else None,
            ]
        ),
        "Required_Reviews": target,
        "Assignment_Shortages": [
            {
                "Project_Number": row["Project_Number"],
                "Assigned": row["Assigned_Judges"],
                "Target": target,
            }
            for row in coverage["coverage"]
            if target
            and row["Judging_Eligible"] is True
            and any(
                p.Project_ID == row["Project_ID"] and not p.Roster_Review_Required
                for p in projects
            )
            and row["Assigned_Judges"] < target
        ],
    }
