"""Previewed CSV imports with explicit identities and atomic, stale-safe apply."""

import csv
import io

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.models.judge import Judge
from app.models.judge_assignment import JudgeAssignment
from app.models.judge_conflict import JudgeConflict
from app.models.mentor_review import MentorReview
from app.models.project import Project
from app.models.score import Score
from app.schemas.judge import JudgeCreate
from app.schemas.mentor_review import MentorDecision
from app.services.access_code import unique_access_code
from app.services.judge_profile import change_name
from app.services.mentor_review import apply_decision, digest, review_workspace

JUDGE_COLUMNS = ["Judge_ID", "First_Name", "Last_Name", "Email", "Department"]
DECISION_COLUMNS = [
    "Judge_ID",
    "Judge_Name",
    "Project_Number",
    "Presenter_Name",
    "Advisor_Name",
    "Review_Context",
    "Decision",
    "Note",
]


def read_rows(content, kind):
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")), strict=True)
        columns = reader.fieldnames or []
        allowed = JUDGE_COLUMNS if kind == "judges" else DECISION_COLUMNS
        required = (
            {"First_Name", "Last_Name"}
            if kind == "judges"
            else {"Judge_ID", "Project_Number", "Review_Context", "Decision", "Note"}
        )
        if (
            len(columns) != len(set(columns))
            or not required <= set(columns)
            or set(columns) - set(allowed)
        ):
            raise HTTPException(422, "Use the supplied CSV template column headings")
        rows = list(reader)
        if len(rows) > 20000:
            raise HTTPException(422, "Upload at most 20,000 rows at a time")
        if any(
            None in row or any(value is None for value in row.values()) for row in rows
        ):
            raise HTTPException(
                422, "Each CSV row must have the same columns as its header"
            )
        return [{key: value.strip() for key, value in row.items()} for row in rows]
    except (UnicodeDecodeError, csv.Error) as exc:
        raise HTTPException(422, "Upload a UTF-8 CSV file") from exc


async def import_context(db, event_id, content):
    snapshot = []
    for model in (Judge, Project, MentorReview, JudgeConflict, JudgeAssignment, Score):
        columns = [c for c in model.__table__.columns if c.name != "Access_Code"]
        query = select(*columns)
        if model in (Judge, Project):
            query = query.where(model.Event_ID == event_id)
        elif model is Score:
            query = query.join(Project, Project.Project_ID == Score.Project_ID).where(
                Project.Event_ID == event_id
            )
        else:
            query = query.join(Judge, Judge.Judge_ID == model.Judge_ID).where(
                Judge.Event_ID == event_id
            )
        rows = (await db.execute(query)).all()
        snapshot.append(sorted([tuple(row) for row in rows], key=str))
    return digest([content.decode("utf-8-sig"), snapshot])


async def preview_import(db, event_id, kind, content):
    rows = read_rows(content, kind)
    judges = list(await db.scalars(select(Judge).where(Judge.Event_ID == event_id)))
    by_id = {j.Judge_ID: j for j in judges}
    plans, errors, seen, seen_names, seen_emails, workspaces = (
        [],
        [],
        set(),
        set(),
        set(),
        {},
    )
    for number, row in enumerate(rows, 2):
        if not any(row.values()) or (kind == "decisions" and not row["Decision"]):
            continue
        try:
            if kind == "judges":
                data = JudgeCreate(
                    Event_ID=event_id,
                    **{
                        key: row.get(key) or None
                        for key in ("First_Name", "Last_Name", "Email", "Department")
                    },
                )
                judge_id = row.get("Judge_ID") or None
                judge = by_id.get(judge_id)
                if judge_id and not judge:
                    raise ValueError("Judge_ID does not belong to this event")
                if judge:
                    if "Email" not in row:
                        data.Email = judge.Email
                    if "Department" not in row:
                        data.Department = judge.Department
                if any(
                    len(value or "") > 200 for value in (data.Email, data.Department)
                ):
                    raise ValueError(
                        "Email and Department must be 200 characters or fewer"
                    )
                name = (data.First_Name.casefold(), data.Last_Name.casefold())
                email = (data.Email or "").casefold()
                if (
                    (judge_id and judge_id in seen)
                    or (not judge_id and name in seen_names)
                    or (email and email in seen_emails)
                ):
                    raise ValueError("Duplicate judge identity in this upload")
                if not judge_id and any(
                    (j.First_Name.casefold(), j.Last_Name.casefold()) == name
                    or (email and (j.Email or "").casefold() == email)
                    for j in judges
                ):
                    raise ValueError(
                        "Possible existing judge. Supply their Judge_ID from the "
                        "review page; names/emails are not identity proof"
                    )
                seen.add(judge_id)
                seen_names.add(name)
                if email:
                    seen_emails.add(email)
                plans.append(
                    {
                        "Row": number,
                        "Action": "update" if judge else "create",
                        "Judge_ID": judge_id,
                        "Current_Name": (
                            f"{judge.First_Name} {judge.Last_Name}" if judge else None
                        ),
                        **data.model_dump(exclude={"Event_ID"}),
                    }
                )
            else:
                judge_id = row["Judge_ID"]
                if judge_id not in by_id:
                    raise ValueError(
                        "Judge_ID does not belong to this event; "
                        "import the judge roster first"
                    )
                if judge_id not in workspaces:
                    workspaces[judge_id] = await review_workspace(
                        db, event_id, judge_id, include_coverage=False
                    )
                project = next(
                    (
                        p
                        for p in workspaces[judge_id]["Projects"]
                        if p["Project_Number"] == row["Project_Number"]
                    ),
                    None,
                )
                if not project:
                    raise ValueError("Project_Number does not belong to this event")
                pair = (judge_id, project["Project_ID"])
                if pair in seen:
                    raise ValueError("Duplicate judge/presentation relationship")
                seen.add(pair)
                decision = MentorDecision(
                    Context=row["Review_Context"],
                    Decision=row["Decision"],
                    Note=row["Note"],
                )
                if decision.Context != project["Context"]:
                    raise ValueError(
                        "Review context is outdated. Download a fresh decision "
                        "sheet and recheck this relationship"
                    )
                if decision.Decision == "clear" and project["Conflict_ID"] is not None:
                    raise ValueError(
                        "Resolve the recorded conflict in Competition setup "
                        "before marking clear"
                    )
                plans.append(
                    {
                        "Row": number,
                        "Judge_ID": judge_id,
                        "Judge_Name": (
                            f"{by_id[judge_id].First_Name} {by_id[judge_id].Last_Name}"
                        ),
                        "Project_ID": project["Project_ID"],
                        "Project_Number": project["Project_Number"],
                        "Decision": decision.Decision,
                        "Note": decision.Note,
                        "Assignment_Removed": decision.Decision == "conflict"
                        and project["Assigned"],
                        "Historical_Scores_Excluded": decision.Decision == "conflict"
                        and project["Has_Scores"],
                    }
                )
        except (ValueError, ValidationError) as exc:
            message = (
                str(exc)
                if not isinstance(exc, ValidationError)
                else "; ".join(e["msg"] for e in exc.errors())
            )
            errors.append(f"Row {number}: {message}")
    return {
        "Rows": plans,
        "Errors": errors,
        "Context": await import_context(db, event_id, content),
        "Applied": False,
    }


async def apply_import(db, event_id, kind, preview, reviewer):
    for row in preview["Rows"]:
        if kind == "judges":
            judge = await db.get(Judge, row["Judge_ID"]) if row["Judge_ID"] else None
            if not judge:
                judge = Judge(
                    Event_ID=event_id,
                    Access_Code=await unique_access_code(db),
                    First_Name=row["First_Name"],
                    Last_Name=row["Last_Name"],
                )
                db.add(judge)
            else:
                change_name(judge, row["First_Name"], row["Last_Name"])
            judge.Email, judge.Department = row["Email"], row["Department"]
            await db.flush()
        else:
            await apply_decision(
                db,
                row["Judge_ID"],
                row["Project_ID"],
                row["Decision"],
                row["Note"],
                reviewer,
            )
    await db.commit()
    return {**preview, "Applied": True}


def csv_content(columns, rows):
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
