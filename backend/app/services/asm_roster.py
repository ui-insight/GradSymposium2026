"""Stage every source submission without deciding acceptance or merging revisions."""

import hashlib
import re
import uuid
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.project import Project
from app.schemas.project import ProjectCreate
from app.services.project_numbering import lock_event_numbers, reserve_number

POSTER_CHOICE = "A poster at the main conference"


def prepare_submissions(values, filename: str, digest: str, sheet: str) -> list[dict]:
    if not values:
        raise ValueError("The response sheet is empty")
    headers = {str(value).strip(): index for index, value in enumerate(values[0])}
    required = (
        "Abstract title",
        "Presenting author",
        "Presenting author email address",
        "Your current position",
        "Please check the appropriate box(es) if you would like to be considered for:",
        "PI/ Lab name",
        "Institution",
        "Timestamp",
    )
    if missing := set(required) - headers.keys():
        raise ValueError(f"Missing source columns: {', '.join(sorted(missing))}")
    submissions = []
    for source_row, row in enumerate(values[1:], start=2):
        if not any(value is not None and str(value).strip() for value in row):
            continue

        def cell(name):
            index = headers[name]
            value = row[index] if index < len(row) else None
            return str(value).strip() if value is not None else ""

        title, name = cell("Abstract title"), cell("Presenting author")
        if not title or not name:
            raise ValueError(f"Source row {source_row}: Missing title or presenter")
        email = cell("Presenting author email address")
        choices = cell(required[4])
        flags = []
        if POSTER_CHOICE not in choices:
            flags.append("talk_only")
        if (
            "," in email
            or ";" in email
            or re.search(r"[,;]|\s+(?:and|&)\s+", name, re.I)
        ):
            flags.append("co_presenters")
        submissions.append(
            {
                "source_key": hashlib.sha256(
                    f"{digest}|{sheet}|{source_row}".encode()
                ).hexdigest(),
                "title": title,
                "presenter": name,
                "email": email or None,
                "institution": cell("Institution") or None,
                "advisor": cell("PI/ Lab name") or None,
                "review": {
                    "source_file": filename,
                    "source_sha256": digest,
                    "source_sheet": sheet,
                    "source_row": source_row,
                    "submitted_at": cell("Timestamp"),
                    "requested_formats": choices,
                    "current_position": cell("Your current position"),
                    "flags": flags,
                    "duplicate_rows": [],
                },
            }
        )
    if not submissions:
        raise ValueError("No submissions found")

    by_contact, by_title = defaultdict(list), defaultdict(list)
    for item in submissions:
        by_contact[(item["email"] or item["presenter"]).casefold()].append(item)
        by_title[item["title"].casefold()].append(item)
    for group in [*by_contact.values(), *by_title.values()]:
        if len(group) > 1:
            source_rows = [item["review"]["source_row"] for item in group]
            for item in group:
                review = item["review"]
                if "duplicate" not in review["flags"]:
                    review["flags"].append("duplicate")
                review["duplicate_rows"] = sorted(
                    set(review["duplicate_rows"]) | set(source_rows)
                )
    return submissions


async def stage_submissions(
    db: AsyncSession, event_id: str, submissions: list[dict]
) -> dict:
    """Import one snapshot atomically. Caller commits after writing its report."""
    await lock_event_numbers(db, event_id)
    event = await db.get(Event, event_id)
    existing = list(
        await db.scalars(select(Project).where(Project.Event_ID == event_id))
    )
    expected_keys = {item["source_key"] for item in submissions}
    if len(expected_keys) != len(submissions):
        raise ValueError("Source submission keys are not unique")
    if any(project.Source_Submission_Key not in expected_keys for project in existing):
        raise ValueError(
            "Use an empty event or the identical source snapshot; "
            "existing roster differs"
        )
    by_key = {project.Source_Submission_Key: project for project in existing}
    event.Public_Poster_Lookup_Enabled = False
    imported = 0
    records = []
    for item in submissions:
        project = by_key.get(item["source_key"])
        if project is None:
            payload = ProjectCreate(
                Event_ID=event_id,
                Category="Poster",
                Project_Title=item["title"],
                Presenter_Display_Name=item["presenter"],
                Presenter_Email=item["email"],
                Institution=item["institution"],
                Advisor_Name=item["advisor"],
            )
            project_id = str(uuid.uuid4())
            number = await reserve_number(db, event_id, project_id, "Poster")
            project = Project(
                **payload.model_dump(exclude={"Project_Number"}),
                Project_ID=project_id,
                Project_Number=number,
                Source_Submission_Key=item["source_key"],
                Roster_Review=item["review"],
                Roster_Review_Required=bool(
                    set(item["review"]["flags"]) & {"duplicate", "talk_only"}
                ),
                Is_Active=True,
                Is_Published=False,
            )
            db.add(project)
            imported += 1
        else:
            # Refresh source annotations, while preserving numbers and organizer edits.
            project.Roster_Review = {**(project.Roster_Review or {}), **item["review"]}
        project.Is_Published = False
        records.append(
            {
                "project_id": project.Project_ID,
                "number": project.Project_Number,
                "presenter": project.Presenter_Display_Name,
                "title": project.Project_Title,
                "review_required": project.Roster_Review_Required,
                "review": project.Roster_Review,
            }
        )
    await db.flush()
    groups = {
        tuple(item["review"]["duplicate_rows"])
        for item in submissions
        if item["review"]["duplicate_rows"]
    }
    return {
        "event_id": event_id,
        "source_file": submissions[0]["review"]["source_file"],
        "source_sha256": submissions[0]["review"]["source_sha256"],
        "source_sheet": submissions[0]["review"]["source_sheet"],
        "source_submissions": len(submissions),
        "imported": imported,
        "already_loaded": len(submissions) - imported,
        "poster_requested": sum(
            "talk_only" not in item["review"]["flags"] for item in submissions
        ),
        "talk_only": sum(
            "talk_only" in item["review"]["flags"] for item in submissions
        ),
        "duplicate_groups": [list(rows) for rows in sorted(groups)],
        "review_required": sum(record["review_required"] for record in records),
        "published": False,
        "records": records,
    }
