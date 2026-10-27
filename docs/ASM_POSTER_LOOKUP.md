# ASM poster numbering and public lookup

## Current implementation

- Public lookup is at `/posters`, linked from the home page.
- New posters receive `P-001`, `P-002`, etc. Existing issued formats are preserved.
- Number reservations persist independently of the project, including after
  withdrawal or deletion. Numbers cannot be changed through project editing.
- CSV import supports rollback-only previews and atomic draft imports. Identical
  repeat uploads skip existing records. Duplicate submissions, changed records,
  and possible title revisions are flagged for review.
- Full presenter display names support co-presenters. Institution and board/table
  location are separate fields.
- The admin Projects page provides preview/import, correction, publication,
  withdrawal/reinstatement, and a public-lookup QR code.
- Publication releases all active posters in the selected active event. Imports,
  edits, and reinstated posters remain drafts until another publication action.
- Public responses include only the conference name/date/location and published
  poster numbers, titles, presenter display names, institutions, and locations.
  Contact details, scores, judge credentials, and internal IDs are excluded.
- The public page can print the currently filtered directory.

Paul's source abstract workbook is now loaded into `backend/asm-draft.db` as 108
unpublished candidates, numbered P-001 through P-108 in worksheet order. The
synthetic demo database remains separate. Four rows across two duplicate pairs
and 11 talk-only submissions are flagged, giving 15 rows requiring decisions.
Three records containing possible co-presenters retain their shared display names.
The original workbook is unchanged. Paul still needs to confirm the final roster,
duplicate resolutions, inclusion decisions, and board layout. Rubric configuration
and attendee voting remain later implementation work.

The admin Projects page has searchable review filters and source row references.
The source-review report is in `data/asm-2026/roster-review.md` with a JSON import
manifest alongside it. Runtime databases and review reports are ignored by Git.

## Reload the source snapshot as drafts

From `backend/`, use the dedicated draft database:

```bash
export GPSA_DATABASE_URL=sqlite+aiosqlite:///./asm-draft.db
export GPSA_SEED_HISTORICAL_EVENT=false
.venv/bin/python -m app.commands.import_asm_roster '../ASM NW Branch Meeting Abstract Form 2026 (Responses).xlsx' --report ../data/asm-2026/roster-review.json
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

This staging command retains every response row, including duplicates and
talk-only requests. A candidate number is not an acceptance decision. Repeating
the identical snapshot preserves IDs, numbers, and organizer corrections while
refreshing source annotations. A different source snapshot is rejected when it
would mix with an existing roster. Each source row is keyed by the workbook
SHA-256, sheet, and row rather than deduplicating by presenter/title.

The command always hides the directory and makes its records unpublished. It is
for draft review; use the admin workflows for later confirmed roster changes.
Publication is blocked while any active record requires roster review. An
unresolved record is also excluded by the public API even if its publication
flag is set independently.

## Separate ASM setup

Use a separate database/volume for ASM. Do not run these commands against the
archived GPSA production database. Historical GPSA auto-seeding must be disabled
through `GPSA_SEED_HISTORICAL_EVENT=false`, including on server restarts.

For a direct local run, from `backend/`:

```bash
source .venv/bin/activate
export GPSA_DATABASE_URL=sqlite+aiosqlite:///./asm-local.db
export GPSA_SEED_HISTORICAL_EVENT=false
python -m app.commands.setup_asm --activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

From `frontend/`, run `npm run dev`. The setup command creates an empty,
unpublished October 31–November 1 event. Re-running it preserves the event,
roster, and publication state. `--activate` deactivates other events in that
database. Omit that flag to create the event inactive.

The command provisions the existing development admin account when none exists.
Use the operations guide to set the live admin password before deployment.

For Docker, start from `.env.asm.example`, replace the secret and database
password, and set the actual public origin. Use a distinct Compose project:

```bash
docker compose --env-file .env.asm -p asm2026 up -d --build
docker compose --env-file .env.asm -p asm2026 exec backend python -m app.commands.setup_asm --activate
```

Store local live settings in `.env.asm` (ignored by Git). The named ASM volume,
Compose project, host port, and subnet keep this instance separate from GPSA.
Confirm hostname/TLS and generate printed QR materials from the final public URL.

## Schema upgrades

The Alembic revision `20261027_poster_lookup` creates the base schema on a fresh
container database, or adds the publication/name/institution fields and reservation
table to an existing installation. Its downgrade preserves the original tables.

Direct app startup retains the repository's existing schema-bootstrap behavior:
create missing tables, apply additive runtime column upgrades, then stamp the
Alembic head. The added publication fields default to false, so upgrading an
existing GPSA database does not expose its roster.

## Prepare and import a roster

Download the CSV template from the admin Projects page. Required columns are
`Title`, `Category`, and either `Presenter_Display_Name` or both `First_Name` and
`Last_Name`. Category is `Poster` for ASM posters.

Optional fields: `Project_Number`, `Email`, `Institution`, `Department`, `College`,
`Advisor`, and `Table_Number`. Quote fields containing commas, especially joint
presenter names. Save as UTF-8 CSV. The source Google Forms response columns need
organizer-reviewed conversion into this template for regular CSV import. The
separate staging command above reads the source XLSX with review flags; browser
XLSX upload is not implemented.

```csv
Title,Presenter_Display_Name,Category,Institution,Table_Number
Example microbial research,"Alex Rivera, Sam Lee",Poster,University of Idaho,B-17
```

1. Resolve inclusion and revision decisions and choose the initial roster order.
   Automatic numbers follow CSV row order for rows without explicit numbers.
   Explicit numbers are reserved first.
2. Use **Preview CSV**. Review every proposed number and presenter. Preview rolls
   back all changes and does not reserve numbers. Another administrator's import
   can change the final numbers before confirmation.
3. Use **Import drafts**. Any validation conflict rejects the whole batch. The
   resulting rows are private drafts. Even a late import into an open directory
   requires publication before its new posters appear.
4. Correct names, titles, institutions, and locations with **Edit**. Edits preserve
   the number and return the poster to draft. For private contact/name-field
   corrections beyond the display name, use the authenticated project PATCH API.
5. Review the complete roster, then **Publish active posters** and confirm. Check
   `/posters` and the directory QR code from an attendee's phone.
6. Use **Hide directory** to withdraw public access without removing records.

An identical import is skipped only when the imported metadata still matches.
If a title changes for a known presenter/contact, the importer requires review
instead of inventing a second presentation. A genuinely distinct presentation by
that presenter can be created explicitly through the admin API. Retain assigned
numbers in future working copies of the roster.

Withdrawing a poster immediately removes it from future public responses and
clears assignments. Reinstatement returns it to draft. A page already open on an
attendee's device refreshes its roster when reloaded; it does not poll for changes.

## API endpoints

| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /api/v1/public/posters` | Public | Allowlisted published directory, with `Cache-Control: no-store` |
| `POST /api/v1/projects/` | Admin | Create a draft; omit `Project_Number` for issuance |
| `POST /api/v1/projects/import-csv?event_id=…&dry_run=true` | Admin | Validate and preview CSV without saving |
| `POST /api/v1/projects/import-csv?event_id=…` | Admin | Commit the draft import |
| `POST /api/v1/projects/publication` | Admin | Body: `Event_ID`, `Is_Published`; publish active posters or hide the directory |
| `PATCH /api/v1/projects/{id}` | Admin | Correct metadata while preserving the number |

The directory fails closed if zero or multiple events are active. Publication
requires exactly one active event. Both event publication and individual poster
publication must be enabled before a poster appears.

## Verification

From `backend/`:

```bash
GPSA_DATABASE_URL=sqlite+aiosqlite:////tmp/asm-tests-unused.db GPSA_SEED_HISTORICAL_EVENT=false .venv/bin/python -m pytest -q
```

Tests create their own temporary databases. Coverage includes rollback previews,
atomic failures, repeat uploads, co-presenters, legacy numbers, deletion and
withdrawal reservations, concurrent issuance, draft/publication behavior, public
field filtering, event isolation, access control, title revisions, and fresh and
existing schema upgrades.

From `frontend/`, run `npm run build` and `npm run lint`. Browser rehearsal uses
synthetic posters in an isolated local database, never the unconfirmed roster.
