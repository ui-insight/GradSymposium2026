"""Atomic final-change CSV previews with explicit identities for corrections."""

import csv
import io
import uuid

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.models.project import Project
from app.models.project_number_reservation import ProjectNumberReservation
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.project_changes import correct_project
from app.services.project_numbering import reserve_number
from app.services.roster_review import (
    append_decision,
    apply_action,
    digest,
    load_roster,
    presenter,
    workspace,
)

COLUMNS = [
    "Project_ID",
    "Project_Number",
    "Action",
    "Title",
    "Presenter_Display_Name",
    "Institution",
    "Advisor",
    "Table_Number",
    "Source_Row",
    "Submitted_At",
    "Source_SHA256",
    "Flags",
    "Review_Context",
    "Reason",
    "Talk_Only_Confirmed",
]
OPTIONAL = {"Email", "Superseded_By"}
METADATA = {
    "Title": "Project_Title",
    "Presenter_Display_Name": "Presenter_Display_Name",
    "Institution": "Institution",
    "Advisor": "Advisor_Name",
    "Table_Number": "Table_Number",
}


def csv_text(columns, rows):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(
            [
                "'" + str(v)
                if str(v).startswith(("=", "+", "-", "@", "\t", "\r"))
                else v
                for v in row
            ]
        )
    return output.getvalue()


def read_csv(content):
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")), strict=True)
        fields = reader.fieldnames or []
        if (
            len(fields) != len(set(fields))
            or not {"Action", "Reason"} <= set(fields)
            or set(fields) - set(COLUMNS) - OPTIONAL
        ):
            raise HTTPException(422, "Use the final roster CSV template headings")
        rows = list(reader)
        if len(rows) > 2000:
            raise HTTPException(422, "Upload at most 2,000 final changes")
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise HTTPException(422, "CSV rows must match the header columns")
        return [{k: v.strip() for k, v in row.items()} for row in rows]
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(422, "Upload a UTF-8 CSV file") from exc


async def plan_changes(db, event_id, content):
    changes_csv = read_csv(content)
    state = await workspace(db, event_id)
    _, projects, _, latest, _ = await load_roster(db, event_id)
    by_id = {p.Project_ID: p for p in projects}
    rows = {r["Project_ID"]: r for r in state["Rows"]}
    reservations = list(
        (
            await db.execute(
                select(
                    ProjectNumberReservation.Project_Number,
                    ProjectNumberReservation.Project_ID,
                )
                .where(ProjectNumberReservation.Event_ID == event_id)
                .order_by(ProjectNumberReservation.Project_Number)
            )
        ).all()
    )
    context = digest(
        [
            state["Context"],
            [r["Context"] for r in state["Rows"]],
            reservations,
            digest(content.decode("utf-8-sig")),
        ]
    )
    plans, errors, seen, added_names = [], [], set(), set()
    added_titles, added_emails = set(), set()
    for line, row in enumerate(changes_csv, 2):
        if not row.get("Action"):
            continue
        try:
            action, reason = row["Action"].lower(), row["Reason"]
            if action not in {"add", "correct", "accept", "withdraw", "reopen"}:
                raise ValueError(
                    "Action must be add, correct, accept, withdraw or reopen"
                )
            if not reason or len(reason) > 500:
                raise ValueError("Provide a reason/source of 1–500 characters")
            if action == "add":
                if row.get("Project_ID") or row.get("Project_Number"):
                    raise ValueError(
                        "New posters must leave ID and number empty "
                        "for permanent number issuance"
                    )
                body = ProjectCreate(
                    Event_ID=event_id,
                    Category="Poster",
                    **{
                        target: row.get(key) or None
                        for key, target in {
                            **METADATA,
                            "Email": "Presenter_Email",
                        }.items()
                    },
                )
                name = (body.Presenter_Display_Name or "").casefold()
                title = body.Project_Title.casefold()
                email = (body.Presenter_Email or "").casefold()
                if (
                    name in added_names
                    or title in added_titles
                    or (email and email in added_emails)
                    or any(
                        presenter(p).casefold() == name
                        or p.Project_Title.casefold() == body.Project_Title.casefold()
                        or (
                            body.Presenter_Email
                            and p.Presenter_Email
                            and p.Presenter_Email.casefold()
                            == body.Presenter_Email.casefold()
                        )
                        for p in projects
                    )
                ):
                    raise ValueError(
                        "Possible existing presenter/title. Correct the existing "
                        "explicit Project_ID instead of adding a duplicate"
                    )
                added_names.add(name)
                added_titles.add(title)
                if email:
                    added_emails.add(email)
                plans.append(
                    {
                        "Row": line,
                        "Action": action,
                        "Reason": reason,
                        "Project_ID": str(uuid.uuid4()),
                        "Project_Number": None,
                        "Presenter_Name": body.Presenter_Display_Name,
                        "Payload": body.model_dump(exclude={"Project_Number"}),
                    }
                )
                continue
            project_id = row.get("Project_ID", "")
            p = by_id.get(project_id)
            if row.get("Email"):
                raise ValueError(
                    "Email is only supported for additions; use the existing "
                    "project editor/API for contact corrections"
                )
            if not p or project_id in seen:
                raise ValueError(
                    "Use one explicit Project_ID from this event per change"
                )
            seen.add(project_id)
            if row.get("Review_Context") != rows[project_id]["Context"]:
                raise ValueError(
                    "Review details changed. Download a fresh change sheet"
                )
            if row.get("Project_Number") and row["Project_Number"] != p.Project_Number:
                raise ValueError("Issued presentation numbers cannot be changed")
            for column, actual in (
                ("Source_Row", str((p.Roster_Review or {}).get("source_row", ""))),
                ("Submitted_At", (p.Roster_Review or {}).get("submitted_at", "")),
                ("Source_SHA256", (p.Roster_Review or {}).get("source_sha256", "")),
                ("Flags", ", ".join((p.Roster_Review or {}).get("flags") or [])),
            ):
                if column in row and row[column] != actual:
                    raise ValueError("Source annotation columns are read-only")
            changes = {
                target: (row[key] or None)
                for key, target in METADATA.items()
                if key in row
            }
            # Undo formula-protection prefixes only when they refer to unchanged data.
            for key in changes:
                old = (
                    presenter(p) if key == "Presenter_Display_Name" else getattr(p, key)
                )
                if changes[key] == "'" + str(old) and str(old).startswith(
                    ("=", "+", "-", "@")
                ):
                    changes[key] = old
            if action == "correct":
                merged = {key: getattr(p, key) for key in ProjectCreate.model_fields}
                merged.update(changes)
                ProjectCreate.model_validate(merged)
            elif any(
                value
                != (
                    presenter(p) if key == "Presenter_Display_Name" else getattr(p, key)
                )
                for key, value in changes.items()
            ):
                raise ValueError(
                    "Use correct to change metadata, then review the corrected record"
                )
            superseded = row.get("Superseded_By") or None
            if superseded and (
                action != "withdraw"
                or superseded == p.Project_ID
                or superseded not in by_id
            ):
                raise ValueError(
                    "Superseded_By must identify another poster in this event "
                    "on a withdrawal"
                )
            if action == "accept" and (
                not p.Is_Active
                or "duplicate" in ((p.Roster_Review or {}).get("flags") or [])
            ):
                raise ValueError(
                    "Use the on-screen review for reinstatement or duplicate acceptance"
                )
            talk_confirmed = row.get("Talk_Only_Confirmed", "").lower() == "true"
            if (
                action == "accept"
                and "talk_only" in ((p.Roster_Review or {}).get("flags") or [])
                and not talk_confirmed
            ):
                raise ValueError(
                    "Set Talk_Only_Confirmed to true after verifying "
                    "poster participation"
                )
            plans.append(
                {
                    "Row": line,
                    "Action": action,
                    "Reason": reason,
                    "Project_ID": project_id,
                    "Project_Number": p.Project_Number,
                    "Presenter_Name": presenter(p),
                    "Title": p.Project_Title,
                    "Payload": changes,
                    "Superseded_By": superseded,
                    "Talk_Only_Confirmed": talk_confirmed,
                    "Assignments_Removed": rows[project_id]["Assigned_Count"]
                    if action == "withdraw"
                    else 0,
                }
            )
        except (ValueError, ValidationError) as exc:
            errors.append(
                f"Row {line}: "
                + (
                    "; ".join(e["msg"] for e in exc.errors())
                    if isinstance(exc, ValidationError)
                    else str(exc)
                )
            )
    if not errors:
        for row in plans:
            if row["Action"] == "add":
                row["Project_Number"] = await reserve_number(
                    db, event_id, row["Project_ID"], "Poster"
                )
    return {"Rows": plans, "Errors": errors, "Context": context, "Applied": False}


async def apply_changes(db, event_id, plan, reviewer):
    for row in plan["Rows"]:
        _, projects, _, latest, _ = await load_roster(db, event_id)
        p = await db.get(Project, row["Project_ID"]) if row["Action"] != "add" else None
        if row["Action"] == "add":
            p = Project(
                **row["Payload"],
                Project_ID=row["Project_ID"],
                Project_Number=row["Project_Number"],
                Is_Active=True,
                Is_Published=False,
                Roster_Review_Required=True,
            )
            db.add(p)
            await db.flush()
            await append_decision(db, p, "pending", row["Reason"], reviewer)
        elif row["Action"] == "correct":
            await correct_project(db, p, ProjectUpdate(**row["Payload"]))
            p.Roster_Review_Required = True
            await append_decision(db, p, "pending", row["Reason"], reviewer)
        else:
            await apply_action(
                db,
                p,
                row["Action"],
                row["Reason"],
                reviewer,
                projects,
                latest,
                row.get("Superseded_By"),
                talk_only_confirmed=row.get("Talk_Only_Confirmed", False),
            )
    await db.commit()
    return {**plan, "Applied": True}
