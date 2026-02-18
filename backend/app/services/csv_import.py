"""CSV import service for bulk project upload."""

import csv
import io

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.schemas.project import CSVImportResult

REQUIRED_COLUMNS = {"Title", "First_Name", "Last_Name", "Category"}

COLUMN_MAP = {
    "project_number": "Project_Number",
    "title": "Project_Title",
    "first_name": "Presenter_First_Name",
    "last_name": "Presenter_Last_Name",
    "email": "Presenter_Email",
    "department": "Department",
    "college": "College",
    "advisor": "Advisor_Name",
    "category": "Category",
    "table_number": "Table_Number",
}


async def import_projects_from_csv(
    db: AsyncSession, event_id: str, file_content: str
) -> CSVImportResult:
    reader = csv.DictReader(io.StringIO(file_content))
    if not reader.fieldnames:
        return CSVImportResult(imported=0, skipped=0, errors=["Empty CSV file"])

    # Normalize header names to lowercase for flexible matching
    header_map: dict[str, str] = {}
    for field in reader.fieldnames:
        normalized = field.strip().lower().replace(" ", "_")
        if normalized in COLUMN_MAP:
            header_map[field] = COLUMN_MAP[normalized]

    missing = REQUIRED_COLUMNS - {
        COLUMN_MAP.get(f.strip().lower().replace(" ", "_"), "")
        for f in reader.fieldnames
    }
    if missing:
        return CSVImportResult(
            imported=0, skipped=0, errors=[f"Missing required columns: {missing}"]
        )

    # Count existing projects to auto-number
    result = await db.execute(
        select(Project).where(Project.Event_ID == event_id)
    )
    existing = result.scalars().all()
    poster_count = sum(1 for p in existing if p.Category == "Poster")
    art_count = sum(1 for p in existing if p.Category == "Art")

    imported = 0
    skipped = 0
    errors: list[str] = []

    for row_num, row in enumerate(reader, start=2):
        try:
            # Map CSV columns to model fields
            mapped: dict[str, str] = {}
            for csv_col, model_col in header_map.items():
                val = row.get(csv_col, "").strip()
                if val:
                    mapped[model_col] = val

            # Validate required fields
            if not mapped.get("Project_Title"):
                skipped += 1
                continue
            if not mapped.get("Presenter_First_Name"):
                skipped += 1
                continue
            if not mapped.get("Presenter_Last_Name"):
                skipped += 1
                continue

            category = mapped.get("Category", "Poster")
            if category not in ("Poster", "Art"):
                errors.append(f"Row {row_num}: Invalid category '{category}'")
                skipped += 1
                continue

            # Auto-generate project number if not provided
            if not mapped.get("Project_Number"):
                if category == "Poster":
                    poster_count += 1
                    mapped["Project_Number"] = f"P-{poster_count:02d}"
                else:
                    art_count += 1
                    mapped["Project_Number"] = f"A-{art_count:02d}"

            project = Project(
                Event_ID=event_id,
                Project_Number=mapped["Project_Number"],
                Project_Title=mapped["Project_Title"],
                Presenter_First_Name=mapped["Presenter_First_Name"],
                Presenter_Last_Name=mapped["Presenter_Last_Name"],
                Presenter_Email=mapped.get("Presenter_Email"),
                Department=mapped.get("Department"),
                College=mapped.get("College"),
                Advisor_Name=mapped.get("Advisor_Name"),
                Category=category,
                Table_Number=mapped.get("Table_Number"),
            )
            db.add(project)
            imported += 1

        except Exception as e:
            errors.append(f"Row {row_num}: {e}")
            skipped += 1

    if imported > 0:
        await db.commit()

    return CSVImportResult(imported=imported, skipped=skipped, errors=errors)
