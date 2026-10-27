# Operations Guide

## Admin Workflows Available Today

Available in the admin UI:

- View the active event dashboard and judge QR code.
- Import projects from CSV.
- Add judges one at a time.
- Print judge access codes.
- Create and clear judge assignments.
- Review results and activity.
- Export final results to Excel.
- Review score submissions and apply score overrides.

Available through FastAPI `/docs` or direct API calls:

- Create an event.
- Update an event, including active/inactive status.
- Bulk-create judges.
- Delete judges or projects.
- Regenerate judge access codes.

Not currently available as a complete workflow in the UI or API:

- Creating a brand-new rubric set for a new event.

For future events, use the SQL rubric-cloning example below.

## First Login

If no admin user exists yet, the backend creates:

- Username: `admin`
- Password: `admin`

Change the password before live use.

## Rotate The Admin Password

Run this from the backend environment:

```bash
cd backend
source .venv/bin/activate
python - <<'PY'
import asyncio
from sqlalchemy import select
from app.auth.password import hash_password
from app.db.engine import async_session_factory
from app.models.user import User

NEW_PASSWORD = "replace-this-before-production"

async def main():
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.Username == "admin"))
        user = result.scalar_one()
        user.Hashed_Password = hash_password(NEW_PASSWORD)
        await session.commit()

asyncio.run(main())
PY
```

If you are using Docker only, run the same snippet with `docker compose exec
backend python - <<'PY'` and the same Python body shown above.

## CSV Import Format For Projects

Required columns:

- `Title`
- `First_Name`
- `Last_Name`
- `Category`

Optional columns:

- `Project_Number`
- `Email`
- `Department`
- `College`
- `Advisor`
- `Table_Number`

Accepted `Category` values:

- `Poster`
- `Art`

Example:

```csv
Project_Number,Title,First_Name,Last_Name,Email,Department,Advisor,Category,Table_Number
P-01,Example Poster,Ada,Lovelace,ada@example.edu,Computer Science,Dr. Smith,Poster,T-01
A-01,Example Art,Jordan,Lee,jordan@example.edu,Art,Prof. Kim,Art,T-A01
```

## Future Symposium Bootstrap

### 1. Log In Through Swagger

Open `/docs`, use `POST /api/v1/auth/login`, copy the bearer token, and use the
Authorize button in Swagger.

### 2. Create The New Event

Use `POST /api/v1/events/` with a body like:

```json
{
  "Event_Name": "2027 Graduate Student Symposium",
  "Event_Date": "2027-03-12",
  "Location": "Bruce Pitman Center - International Ballroom",
  "Description": "Annual GPSA Graduate Student Symposium",
  "Is_Active": true
}
```

Then use `PATCH /api/v1/events/{event_id}` to mark the 2026 event inactive. Keep
only one event active.

### 3. Clone Rubrics Into The New Event

There is no `POST /rubrics` route today, so the easiest path is a direct SQL
copy in PostgreSQL.

Replace `<NEW_EVENT_ID>` with the new event ID returned by `POST /events/`.

```sql
INSERT INTO "Rubric" (
  "Rubric_ID",
  "Event_ID",
  "Rubric_Name",
  "Category",
  "Max_Score",
  "Description"
)
VALUES
  ('rubric-art-2027', '<NEW_EVENT_ID>', 'Art Rubric', 'Art', 9,
   'Scoring rubric for art presentations'),
  ('rubric-poster-2027', '<NEW_EVENT_ID>', 'Poster Rubric', 'Poster', 36,
   'Scoring rubric for poster presentations');

INSERT INTO "Rubric_Criterion" (
  "Rubric_ID",
  "Criterion_Name",
  "Criterion_Group",
  "Description",
  "Min_Score",
  "Max_Score",
  "Sort_Order"
)
SELECT
  'rubric-art-2027',
  "Criterion_Name",
  "Criterion_Group",
  "Description",
  "Min_Score",
  "Max_Score",
  "Sort_Order"
FROM "Rubric_Criterion"
WHERE "Rubric_ID" = (
  SELECT "Rubric_ID" FROM "Rubric"
  WHERE "Event_ID" = 'evt-2026-symposium' AND "Category" = 'Art'
);

INSERT INTO "Rubric_Criterion" (
  "Rubric_ID",
  "Criterion_Name",
  "Criterion_Group",
  "Description",
  "Min_Score",
  "Max_Score",
  "Sort_Order"
)
SELECT
  'rubric-poster-2027',
  "Criterion_Name",
  "Criterion_Group",
  "Description",
  "Min_Score",
  "Max_Score",
  "Sort_Order"
FROM "Rubric_Criterion"
WHERE "Rubric_ID" = (
  SELECT "Rubric_ID" FROM "Rubric"
  WHERE "Event_ID" = 'evt-2026-symposium' AND "Category" = 'Poster'
);
```

Run the SQL with:

```bash
docker compose exec db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

### 4. Load Judges

For a small list, use the admin UI.

For a larger list, use `POST /api/v1/judges/bulk`:

```json
{
  "Event_ID": "<NEW_EVENT_ID>",
  "judges": [
    {
      "Event_ID": "<NEW_EVENT_ID>",
      "First_Name": "Jamie",
      "Last_Name": "Rivera",
      "Email": "jamie@example.edu",
      "Department": "Biology"
    },
    {
      "Event_ID": "<NEW_EVENT_ID>",
      "First_Name": "Morgan",
      "Last_Name": "Patel",
      "Email": "morgan@example.edu",
      "Department": "Art"
    }
  ]
}
```

### 5. Load Projects

Use the Projects page CSV import.

### 6. Assign Judges

Use the Assignments page.

Recommended starting point:

- Poster: 3 judges per project
- Art: 3 judges per project

Use the matrix footer and judge totals to catch under-assigned projects.

### 7. Print Judge Access Codes

Use the Judges page:

- `Print Codes` for handouts
- dashboard QR code for the judge login URL

## During The Event

- Watch the dashboard coverage number.
- Use the Judges page to spot judges with assigned projects but fewer scored
  projects.
- Use Results to inspect submissions, delete a bad submission, or override an
  individual criterion score if needed.
- Export final results from the Results page once scoring is complete.

## After The Event

- Export the results workbook from the Results page.
- Back up the database.
- Archive the final roster source files.
- Record the deployment commit hash and environment used.

## Cleaning Data If You Reuse A Database

If GPSA decides to keep a single database but clear event-specific operational
data, do it only after a confirmed backup.

The safest practical order is:

```sql
DELETE FROM "Score_Override"
WHERE "Score_ID" IN (
  SELECT s."Score_ID"
  FROM "Score" s
  JOIN "Project" p ON p."Project_ID" = s."Project_ID"
  WHERE p."Event_ID" = '<EVENT_ID>'
);

DELETE FROM "Feedback"
WHERE "Project_ID" IN (
  SELECT "Project_ID" FROM "Project" WHERE "Event_ID" = '<EVENT_ID>'
);

DELETE FROM "Score"
WHERE "Project_ID" IN (
  SELECT "Project_ID" FROM "Project" WHERE "Event_ID" = '<EVENT_ID>'
);

DELETE FROM "Judge_Assignment"
WHERE "Project_ID" IN (
  SELECT "Project_ID" FROM "Project" WHERE "Event_ID" = '<EVENT_ID>'
);

DELETE FROM "Judge"
WHERE "Event_ID" = '<EVENT_ID>';

DELETE FROM "Project"
WHERE "Event_ID" = '<EVENT_ID>';
```

Do not clear the database this way unless you already have a dump to restore
from if needed.
