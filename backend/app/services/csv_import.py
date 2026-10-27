"""Validated, atomic roster imports with a rollback-only numbering preview."""

import csv
import io
import uuid

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import CSVImportResult, ProjectCreate, ProjectRead
from app.services.project_numbering import lock_event_numbers, reserve_number

COLUMN_MAP = {
    "project_number": "Project_Number",
    "title": "Project_Title",
    "first_name": "Presenter_First_Name",
    "last_name": "Presenter_Last_Name",
    "presenter_display_name": "Presenter_Display_Name",
    "email": "Presenter_Email",
    "institution": "Institution",
    "department": "Department",
    "college": "College",
    "advisor": "Advisor_Name",
    "category": "Category",
    "table_number": "Table_Number",
}


def _identity(project: Project | ProjectCreate) -> tuple[str, str, str]:
    presenter = project.Presenter_Display_Name or (
        f"{project.Presenter_First_Name} {project.Presenter_Last_Name}"
    )
    contact = project.Presenter_Email or presenter
    return (
        contact.strip().casefold(),
        project.Project_Title.strip().casefold(),
        project.Category,
    )


async def import_projects_from_csv(
    db: AsyncSession, event_id: str, file_content: str, *, dry_run: bool = False
) -> CSVImportResult:
    reader = csv.DictReader(io.StringIO(file_content.lstrip("\ufeff")), strict=True)
    try:
        headers = {
            field: field.strip().lower().replace(" ", "_")
            for field in reader.fieldnames or []
        }
    except csv.Error as exc:
        return CSVImportResult(imported=0, skipped=0, errors=[f"Invalid CSV: {exc}"])
    names = set(headers.values())
    if not {"title", "category"} <= names or not (
        "presenter_display_name" in names or {"first_name", "last_name"} <= names
    ):
        return CSVImportResult(
            imported=0,
            skipped=0,
            errors=[
                "Required: Title, Category, and Presenter_Display_Name "
                "or First_Name/Last_Name"
            ],
        )
    if len(names) != len(reader.fieldnames or []):
        return CSVImportResult(imported=0, skipped=0, errors=["Duplicate CSV headers"])

    rows: list[tuple[int, ProjectCreate]] = []
    errors: list[str] = []
    try:
        for line, row in enumerate(reader, start=2):
            if not any(row.values()):
                continue
            if None in row or any(value is None for value in row.values()):
                errors.append(f"Row {line}: Column count does not match the header")
                continue
            mapped = {
                COLUMN_MAP[headers[key]]: value.strip()
                for key, value in row.items()
                if headers[key] in COLUMN_MAP and value.strip()
            }
            try:
                rows.append((line, ProjectCreate(Event_ID=event_id, **mapped)))
            except ValidationError as exc:
                messages = "; ".join(error["msg"] for error in exc.errors())
                errors.append(f"Row {line}: {messages}")
    except csv.Error as exc:
        errors.append(f"Invalid CSV: {exc}")
    if errors:
        return CSVImportResult(imported=0, skipped=0, errors=errors)

    await lock_event_numbers(db, event_id)
    existing = list(
        await db.scalars(select(Project).where(Project.Event_ID == event_id))
    )
    by_identity = {_identity(project): project for project in existing}
    existing_contacts = {_identity(project)[0] for project in existing}
    by_number = {project.Project_Number: project for project in existing}
    pending: list[tuple[int, ProjectCreate, str]] = []
    seen: set[tuple[str, str, str]] = set()
    skipped = 0
    for line, row in rows:
        identity = _identity(row)
        number = row.Project_Number.strip().upper() if row.Project_Number else None
        if identity in seen:
            errors.append(
                f"Row {line}: Repeated presentation in this CSV; review revisions"
            )
        seen.add(identity)
        match = by_identity.get(identity)
        if match:
            incoming = row.model_dump(
                exclude={
                    "Event_ID",
                    "Project_Number",
                    "Judging_Eligible",
                    "Voting_Eligible",
                    "Award_Groups",
                }
            )
            unchanged = all(
                getattr(match, key) == value for key, value in incoming.items()
            )
            if unchanged and (number is None or number == match.Project_Number):
                skipped += 1
            else:
                errors.append(
                    f"Row {line}: Existing presentation changed; edit its record"
                )
            continue
        if number in by_number:
            errors.append(
                f"Row {line}: Number {number} belongs to another presentation"
            )
            continue
        if identity[0] in existing_contacts:
            errors.append(
                f"Row {line}: Possible title revision for an existing presenter; "
                "edit that record or create a distinct presentation explicitly"
            )
            continue
        pending.append((line, row, str(uuid.uuid4())))

    # Reserve explicit numbers before assigning any automatic numbers.
    numbers: dict[str, str] = {}
    for line, row, project_id in sorted(
        pending, key=lambda item: not bool(item[1].Project_Number)
    ):
        try:
            numbers[project_id] = await reserve_number(
                db, event_id, project_id, row.Category, row.Project_Number
            )
        except ValueError as exc:
            errors.append(f"Row {line}: {exc}")
    if errors:
        await db.rollback()
        return CSVImportResult(imported=0, skipped=skipped, errors=errors)

    projects = [
        Project(
            Project_ID=project_id,
            **row.model_dump(exclude={"Project_Number"}),
            Project_Number=numbers[project_id],
            Is_Active=True,
            Is_Published=False,
        )
        for _, row, project_id in pending
    ]
    db.add_all(projects)
    await db.flush()
    preview = [ProjectRead.model_validate(project) for project in projects]
    result = CSVImportResult(
        imported=len(projects), skipped=skipped, errors=[], preview=preview
    )
    if dry_run:
        await db.rollback()
    else:
        await db.commit()
    return result
