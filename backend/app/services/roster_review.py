"""Final roster evidence, permanent-number reconciliation and publication gate."""

import datetime
import hashlib
import json
import re

from fastapi import HTTPException
from sqlalchemy import func, select

from app.models.event import Event
from app.models.judge_assignment import JudgeAssignment
from app.models.project import Project
from app.models.roster_review import RosterDecision, RosterSignoff
from app.models.score import Score
from app.schemas.public_poster import PublicEvent, PublicPoster
from app.services.project_changes import withdraw_project

SOURCE_FIELDS = (
    "source_file",
    "source_sha256",
    "source_sheet",
    "source_row",
    "submitted_at",
    "requested_formats",
    "current_position",
    "flags",
    "duplicate_rows",
)


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode()
    ).hexdigest()


def presenter(project):
    return (
        project.Presenter_Display_Name
        or f"{project.Presenter_First_Name} {project.Presenter_Last_Name}".strip()
    )


def source(project):
    return (
        {key: (project.Roster_Review or {}).get(key) for key in SOURCE_FIELDS}
        if project.Roster_Review
        else None
    )


def snapshot(project):
    return {
        "Project_ID": project.Project_ID,
        "Project_Number": project.Project_Number,
        "Project_Title": project.Project_Title,
        "Presenter_Name": presenter(project),
        "Institution": project.Institution,
        "Table_Number": project.Table_Number,
        "Source": source(project),
        "Is_Active": project.Is_Active,
    }


def project_context(project):
    return digest(
        [
            snapshot(project),
            project.Source_Submission_Key,
            project.Presenter_First_Name,
            project.Presenter_Last_Name,
            project.Presenter_Email,
            project.Advisor_Name,
            project.Roster_Review_Required,
        ]
    )


def acceptance(project, decision):
    changed = bool(decision and decision.Source_Context != project_context(project))
    if not decision or changed:
        return "pending", changed
    return decision.Decision, False


def number_key(project):
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part.casefold())
        for part in re.split(r"(\d+)", project.Project_Number)
    )


def duplicate_groups(projects):
    by_source = {
        (
            (p.Roster_Review or {}).get("source_sha256"),
            (p.Roster_Review or {}).get("source_sheet"),
            (p.Roster_Review or {}).get("source_row"),
        ): p
        for p in projects
        if p.Roster_Review
    }
    groups = {}
    for p in projects:
        metadata = p.Roster_Review or {}
        rows = metadata.get("duplicate_rows") or []
        if "duplicate" not in (metadata.get("flags") or []) or not rows:
            continue
        key = (
            metadata.get("source_sha256"),
            metadata.get("source_sheet"),
            tuple(sorted(rows)),
        )
        members = [
            by_source[(key[0], key[1], row)]
            for row in rows
            if (key[0], key[1], row) in by_source
        ]
        later = None
        try:
            times = [
                (
                    datetime.datetime.fromisoformat(
                        (m.Roster_Review or {}).get("submitted_at", "")
                    ),
                    m.Project_ID,
                )
                for m in members
            ]
            if len(times) == 2 and times[0][0] != times[1][0]:
                later = max(times)[1]
        except (ValueError, TypeError):
            pass
        groups[key] = {
            "Source_Rows": rows,
            "Project_IDs": [m.Project_ID for m in members],
            "Later_ID": later,
            "Complete_Source": len(members) == len(rows),
        }
    return list(groups.values())


async def load_roster(db, event_id):
    event = await db.get(Event, event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    projects = sorted(
        list(
            await db.scalars(
                select(Project).where(
                    Project.Event_ID == event_id, Project.Category == "Poster"
                )
            )
        ),
        key=number_key,
    )
    history = list(
        await db.scalars(
            select(RosterDecision)
            .join(Project, Project.Project_ID == RosterDecision.Project_ID)
            .where(Project.Event_ID == event_id)
            .order_by(RosterDecision.Decision_ID)
        )
    )
    latest = {r.Project_ID: r for r in history}
    signoff = await db.scalar(
        select(RosterSignoff)
        .where(RosterSignoff.Event_ID == event_id)
        .order_by(RosterSignoff.Signoff_ID.desc())
    )
    return event, projects, history, latest, signoff


def reconcile(event, projects, latest):
    states = {p.Project_ID: acceptance(p, latest.get(p.Project_ID)) for p in projects}
    counts = {
        "Total": len(projects),
        "Accepted": 0,
        "Withdrawn": 0,
        "Pending": 0,
        "Changed": sum(changed for _, changed in states.values()),
        "Source": sum(p.Source_Submission_Key is not None for p in projects),
        "Additions": sum(p.Source_Submission_Key is None for p in projects),
    }
    for status, _ in states.values():
        counts[status.capitalize()] += 1
    sources = {}
    for p in projects:
        if p.Source_Submission_Key:
            metadata = p.Roster_Review or {}
            key = (metadata.get("source_sha256"), metadata.get("source_sheet"))
            group = sources.setdefault(
                key,
                {
                    "SHA256": key[0],
                    "Sheet": key[1],
                    "Rows": [],
                    "Accepted": 0,
                    "Withdrawn": 0,
                    "Pending": 0,
                },
            )
            group["Rows"].append(metadata.get("source_row"))
            group[states[p.Project_ID][0].capitalize()] += 1
    blockers = []
    if any(
        p.Source_Submission_Key
        and not all(
            (p.Roster_Review or {}).get(key)
            for key in ("source_sha256", "source_sheet", "source_row")
        )
        for p in projects
    ):
        blockers.append(
            "Reconcile incomplete source provenance against the private import manifest"
        )
    if counts["Pending"]:
        blockers.append(
            f"Resolve {counts['Pending']} pending or changed inclusion decisions"
        )
    if not counts["Accepted"]:
        blockers.append("Accept at least one poster")
    for group in duplicate_groups(projects):
        members = [p for p in projects if p.Project_ID in group["Project_IDs"]]
        active = [p for p in members if p.Is_Active]
        all_current = all(
            states[p.Project_ID][0] in {"accepted", "withdrawn"} for p in members
        )
        distinct = (
            all(
                (latest[p.Project_ID].Snapshot or {}).get("distinct_verified")
                for p in active
            )
            if all_current
            else False
        )
        superseded = (
            len(active) == 1
            and all(
                latest[p.Project_ID].Superseded_By == active[0].Project_ID
                for p in members
                if not p.Is_Active
            )
            if all_current
            else False
        )
        if (
            not group["Complete_Source"]
            or not all_current
            or (active and not distinct and not superseded)
        ):
            blockers.append(
                "Resolve duplicate source rows "
                + "/".join(map(str, group["Source_Rows"]))
            )
    context = digest(
        [
            PublicEvent.model_validate(event).model_dump(mode="json"),
            [
                (
                    p.Project_ID,
                    project_context(p),
                    latest[p.Project_ID].Decision_ID
                    if p.Project_ID in latest
                    else None,
                )
                for p in projects
            ],
        ]
    )
    return counts, list(sources.values()), blockers, context, states


async def final_roster_ready(db, event_id):
    event, projects, history, latest, signoff = await load_roster(db, event_id)
    required = (
        any(p.Source_Submission_Key for p in projects)
        or bool(history)
        or signoff is not None
    )
    if not required:
        return True  # Existing unrelated events retain their publication workflow.
    _, _, blockers, context, _ = reconcile(event, projects, latest)
    return bool(signoff and signoff.Context == context and not blockers)


async def workspace(db, event_id):
    event, projects, history, latest, signoff = await load_roster(db, event_id)
    counts, sources, blockers, context, states = reconcile(event, projects, latest)
    assigned = dict(
        (
            await db.execute(
                select(JudgeAssignment.Project_ID, func.count())
                .join(Project, Project.Project_ID == JudgeAssignment.Project_ID)
                .where(Project.Event_ID == event_id)
                .group_by(JudgeAssignment.Project_ID)
            )
        ).all()
    )
    scored = dict(
        (
            await db.execute(
                select(Score.Project_ID, func.count())
                .join(Project, Project.Project_ID == Score.Project_ID)
                .where(Project.Event_ID == event_id)
                .group_by(Score.Project_ID)
            )
        ).all()
    )

    def read_decision(record):
        return {
            "Decision_ID": record.Decision_ID,
            "Decision": record.Decision,
            "Reason": record.Reason,
            "Recorded_By": record.Recorded_By,
            "Recorded_At": record.Recorded_At,
            "Superseded_By": record.Superseded_By,
            "Snapshot": record.Snapshot,
        }

    rows = []
    for p in projects:
        record = latest.get(p.Project_ID)
        rows.append(
            {
                **snapshot(p),
                "Advisor_Name": p.Advisor_Name,
                "Judging_Eligible": p.Judging_Eligible,
                "Voting_Eligible": p.Voting_Eligible,
                "Acceptance": states[p.Project_ID][0],
                "Changed": states[p.Project_ID][1],
                "Is_Published": p.Is_Published,
                "Assigned_Count": assigned.get(p.Project_ID, 0),
                "Score_Count": scored.get(p.Project_ID, 0),
                "Context": digest(
                    [
                        project_context(p),
                        record.Decision_ID if record else None,
                        assigned.get(p.Project_ID, 0),
                        scored.get(p.Project_ID, 0),
                    ]
                ),
                "Decision": read_decision(record) if record else None,
                "History": [
                    read_decision(r) for r in history if r.Project_ID == p.Project_ID
                ],
            }
        )
    accepted = [
        p for p in projects if states[p.Project_ID][0] == "accepted" and p.Is_Active
    ]
    return {
        "Event_ID": event_id,
        "Event_Name": event.Event_Name,
        "Final_Review_Required": any(p.Source_Submission_Key for p in projects)
        or bool(history)
        or signoff is not None,
        "Counts": counts,
        "Sources": sources,
        "Rows": rows,
        "Duplicate_Groups": duplicate_groups(projects),
        "Blockers": blockers,
        "Context": context,
        "Signoff": {
            "Signed_By": signoff.Signed_By,
            "Signed_At": signoff.Signed_At,
            "Reference": signoff.Reference,
            "Accepted_Count": signoff.Accepted_Count,
            "Current": signoff.Context == context and not blockers,
        }
        if signoff
        else None,
        "Preview": {
            "event": PublicEvent.model_validate(event).model_dump(mode="json"),
            "posters": [
                PublicPoster(
                    Project_Number=p.Project_Number,
                    Project_Title=p.Project_Title,
                    Presenter_Display_Name=presenter(p),
                    Institution=p.Institution,
                    Table_Number=p.Table_Number,
                ).model_dump()
                for p in accepted
            ],
        },
    }


async def append_decision(
    db,
    project,
    decision,
    reason,
    reviewer,
    superseded_by=None,
    distinct=False,
    talk_only_confirmed=False,
):
    record = RosterDecision(
        Project_ID=project.Project_ID,
        Decision=decision,
        Reason=reason,
        Source_Context=project_context(project),
        Snapshot={
            **snapshot(project),
            "distinct_verified": distinct,
            "talk_only_confirmed": talk_only_confirmed,
        },
        Superseded_By=superseded_by,
        Recorded_By=reviewer,
        Recorded_At=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
    )
    db.add(record)
    await db.flush()


async def apply_action(
    db,
    project,
    action,
    reason,
    reviewer,
    all_projects,
    latest,
    superseded_by=None,
    distinct=False,
    talk_only_confirmed=False,
):
    if action == "accept":
        if (
            "talk_only" in ((project.Roster_Review or {}).get("flags") or [])
            and not talk_only_confirmed
        ):
            raise HTTPException(
                409,
                "Explicitly confirm poster participation for this talk-only request",
            )
        if not project.Is_Active:
            raise HTTPException(
                409, "Reinstate this poster for review before accepting it"
            )
        if (
            "duplicate" in ((project.Roster_Review or {}).get("flags") or [])
            and not distinct
        ):
            for group in duplicate_groups(all_projects):
                if project.Project_ID not in group["Project_IDs"]:
                    continue
                for other in all_projects:
                    if (
                        other.Project_ID in group["Project_IDs"]
                        and other.Project_ID != project.Project_ID
                    ):
                        previous = latest.get(other.Project_ID)
                        if (
                            other.Is_Active
                            or not previous
                            or acceptance(other, previous)[0] != "withdrawn"
                            or previous.Superseded_By != project.Project_ID
                        ):
                            raise HTTPException(
                                409,
                                "Resolve the duplicate comparison first, or "
                                "explicitly verify distinct presentations",
                            )
        project.Roster_Review_Required = False
        decision = "accepted"
    elif action == "withdraw":
        await withdraw_project(db, project)
        project.Roster_Review_Required = False
        decision = "withdrawn"
    else:
        project.Is_Active = True
        project.Roster_Review_Required = True
        decision = "pending"
    project.Is_Published = False
    await append_decision(
        db,
        project,
        decision,
        reason,
        reviewer,
        superseded_by,
        distinct,
        talk_only_confirmed,
    )
