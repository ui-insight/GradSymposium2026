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
duplicate resolutions, inclusion decisions, and board layout. Judging and attendee voting are implemented; see
`docs/ASM_COMPETITION_READINESS.md` for Paul’s rubric setup and remaining decisions.

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

Use **Approve inclusion** on a flagged active submission after checking its source
details. Confirm the decision to clear its review block while keeping it in draft;
the source annotations retain the approving admin ID and UTC timestamp. Withdraw
superseded duplicates or submissions that should not be included. Approval does
not publish the directory, and re-staging the identical snapshot preserves it.

Flag approval alone is not final roster approval. For staged source events, use
**Final roster review** to record the complete accepted/withdrawn/pending list,
reconcile the source count and record an organizer sign-off of the exact preview.
Publication requires that current sign-off. Historical events without source
annotations or final-review history retain their existing publication workflow.

## Final roster review

Open **Final roster review** in Administration and select the intended event.
All source candidates and later additions need an explicit final inclusion
decision, including source rows without original warning flags. Acceptance never
sets judging eligibility, voting eligibility or award groups.

1. Check the source counts, sheet and SHA-256 against the private import manifest
   and unchanged workbook. Source candidates plus later additions must reconcile
   to accepted + withdrawn + pending. Source-linked records cannot be deleted.
2. Compare each duplicate pair side by side. The interface displays the complete
   names/titles, original row numbers and timestamps as recorded. Confirm the
   source details before keeping the strictly later version and withdrawing its
   predecessor. This is atomic and records the retained Project_ID as provenance;
   both numbers remain reserved. Unknown/equal/incomparable timestamps require
   source clarification. Do not guess. If a flag represents genuinely different
   presentations, explicitly verify that distinction with a recorded reason.
3. Filter talk-only requests and record each inclusion/exclusion. Acceptance
   requires an explicit organizer confirmation of poster participation. For
   ordinary candidates, select the reviewed records, choose an action and record
   a source/reason. Blank decisions never count as acceptance.
4. Correct existing records with **Correct metadata**, preserving their IDs and
   numbers. Keep full co-presenter names together. Corrections return inclusion
   to pending; decision history retains earlier names/titles and reviewers.
5. Use **Upload final additions, corrections and removals** for reviewed CSV
   changes. Download the current change sheet. Set `Action` to `add`, `correct`,
   `accept`, `withdraw` or `reopen` and supply `Reason`. Blank actions are skipped;
   omitted rows do not withdraw anything. Existing changes require the exact
   Project_ID, unchanged issued number and current Review_Context. Source columns
   are read-only. For talk-only acceptance set `Talk_Only_Confirmed=true`.
   Resolve duplicate acceptance through the on-screen comparison.
6. For `add`, leave ID and number empty and supply `Title` and full
   `Presenter_Display_Name`; institution, advisor, location and optional `Email`
   may be supplied. Possible existing names, contacts and titles require review
   against the existing record rather than accidental duplicate creation. New
   drafts receive the next unused number and still need an inclusion decision.
   Existing contact corrections use the authenticated project PATCH API; the
   final-change sheet does not export private contacts.
7. Preview every CSV change before applying. Any error prevents the entire batch.
   A concurrent roster, assignment, score-count or numbering change requires a
   fresh preview. Number previews roll back reservations. Existing IDs/numbers
   are never reassigned, even after withdrawal or reinstatement.
8. Open the accepted-only directory preview. It includes the attendee fields only,
   with full co-presenters and unassigned locations labelled clearly. Confirm the
   accepted count and original source count, record the organizer approval
   reference, and attest that final changes/talk-only decisions and the preview
   were checked. Signing off does not publish.
9. Download the reconciliation/operating report and retain it in the private
   operating guide. It records counts, source hashes, sign-off/reference and the
   accepted directory without private contacts, PI/lab text or source workbooks.
   Use **Publication and eligibility controls** for the separate publication step.

Decisions are append-only and scoped to an authenticated administrator. Withdrawal
clears assignments while retaining scores and decision history. Reinstatement
returns the record to pending. Metadata corrections, additions/removals or new
inclusion decisions invalidate the prior exact-content sign-off. For final-review
events the ordinary published directory then fails closed until a new sign-off;
corrected/new records remain drafts until republished. Competition eligibility
changes alone do not invalidate acceptance or final roster sign-off.

The explicit public dev **draft** preview remains a separate testing mode. It can
show unconfirmed active candidates and is not the accepted-only final preview.
No real final additions/removals, talk-only choices or organizer sign-off have
been applied by implementing this workflow. Issue #11 remains an organizer task.

## Separate ASM setup

### Public dev preview

For organizer testing on dev, set both `GPSA_DEV_MODE=true` and
`GPSA_PUBLIC_DRAFT_PREVIEW=true`, then recreate the backend container. This makes
all active poster drafts in the sole active event publicly searchable at
`/posters`, including flagged submissions, with an unconfirmed-draft notice that
also appears when printing. Only the usual public fields are returned. Private
contacts, source annotations, review decisions, and scores remain excluded.

This preview does not change `Is_Published`, clear review flags, or approve any
submission. Normal publication still requires resolving the active review flags.
The preview is disabled by default and ignored when `GPSA_DEV_MODE=false`.
Set `GPSA_PUBLIC_DRAFT_PREVIEW=false` to return to the published-only directory.

The current dev setup uses ASM as the active event and preserves the historical
GPSA event as inactive. Keep `GPSA_SEED_HISTORICAL_EVENT=false` in dev settings so
backend restarts do not re-enable the historical event.

### Isolated live deployment

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
5. Approve inclusion for flagged submissions you are keeping, and withdraw those
   you are excluding. For source/final-review events, complete **Final roster
   review** and its sign-off. Review the complete roster, then **Publish active posters**
   and confirm. Check
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

## Board and session convention (#12)

Open **Boards and sessions** (`/admin/poster-sessions`) for the selected event.
The session mapping starts unconfigured. Board labels always follow valid issued
poster numbers. No odd/even mapping or times are seeded;
Paul must confirm which parity belongs to Session I and Session II and supply
both complete date/time/time-zone labels. These are display labels, not judging
schedules, eligibility rules or voting pools.

Preview the proposal before applying it. Board labels use the exact permanent
presentation number (`P-001`, `P-108`); sessions use the positive ASCII numeric
suffix's parity. Manual board/table locations remain separate and appear as
additional location details. Withdrawn numbers stay reserved and are omitted
from the printable setup list. Late additions automatically follow the confirmed
convention without moving any existing presentation.

Unexpected number formats are flagged in the private preview and receive no
guessed board/session. Applying a convention with flagged active records requires
explicit acknowledgement that they remain unassigned for organizer follow-up.
A changed roster or convention requires a new preview. Apply also requires a
completed final roster review, an organizer confirmation reference, and explicit
confirmation of the parity, both time labels and preview.

Public lookup, judge project list/detail, accepted-directory preview and the
operating report share the same derived board/session fields. Applying a changed
convention invalidates the exact-directory signoff; review and sign off the new
preview before republishing. Public allowlisting and unpublished-roster protection
remain in force. Draft setup printouts retain a draft label. The real ASM mapping
remains unconfigured until Paul's confirmation.
