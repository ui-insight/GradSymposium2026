# ASM Northwest Branch Meeting 2026: customization plan

Prepared October 27, 2026.

## Implementation status

Numbering and lookup are deployed on dev, including Barrie's explicitly enabled
public draft preview of the 108 source responses. Fifteen source inclusion
decisions remain pending; no duplicate was merged or talk-only request accepted
automatically. Preview visibility is separate from formal publication.

Judging and attendee voting foundations are now implemented with organizer rule
editors, eligibility, conflicts, review targets, valid complete-review counting,
ballot entitlements and exports. Real ASM judging and voting remain closed with
rules pending. A separate synthetic event supports rehearsal. See the current
[competition readiness and operating guide](ASM_COMPETITION_READINESS.md) for
implemented capabilities, test coverage and limitations. Paul's four-criterion
0–5 rubric and inline help are implemented (20 points per review); install the
draft with the command in that guide. Session-restricted ballots, ranked vote
weighting and attendee award grouping
still depend on the organizer's selected rules.

The sections below retain the original plan and source evidence; their initial
gap descriptions are historical, not the current implementation status.

## Recommended scope

Confirmed scope: poster numbering, public poster lookup, rubric judging, and
attendee voting. Deliver numbering, lookup, and printable setup materials first,
then complete both evaluation workflows before the conference rehearsal.

All four features share the accepted poster roster and permanent numbers.
Rubric judging and attendee voting have separate permissions, submission rules,
results, and exports. The remaining decisions concern their rules and operation.

Paul's email asks whether the app can assign numbers and let attendees find their
poster number so they can pin their poster in the correct place for judging.
Assign a number to each accepted poster presentation. Co-presenters share that
poster number. If Paul also wants attendee registration numbers, treat those as
a separate requirement: the abstract workbook is not an attendee roster.

Use the existing React/FastAPI app with an ASM-specific deployment and database.
Retain the GPSA archive. Avoid a general conference-management redesign before
the October 31 opening.

## Evidence and roster reconciliation

Sources reviewed:

- Paul's local email file, subject `109 posters!`, sent October 26
  Pacific time / October 27 UTC.
- The local abstract-response workbook,
  worksheet `Form Responses 1`, range `A1:J109`.
- The local conference-announcement email.
- Local schedule text, supplied alongside the
  schedule PDF. Treat these times as the supplied draft until confirmed.
- Current application source and the handoff, operations, and deployment guides.

| Observation | Planning consequence |
| --- | --- |
| Paul's email says 109 posters. The sheet has 109 rows including its header, or 108 responses. | Confirm the final count. Do not publish a numbered roster based on 109. |
| 97 responses select `A poster at the main conference`. Eleven select talks only. | Presentation preferences are requests, not final acceptance decisions. Ask whether talk applicants will also present posters. |
| Spreadsheet rows 6 and 9 share a presenter, title, and email. Rows 92 and 109 form another such pair. | Review these as possible revisions. Preserve both original submissions and record which version is accepted. |
| Both duplicate candidates are among the poster selections. Collapsing each pair would yield 95 candidate poster records. | 95 is a conditional reconciliation count, not a confirmed conference total. |
| Row 38 lists two co-presenters with two email addresses. | Preserve both presenter names, allow lookup by either, and assign one poster number. Do not split this into two posters automatically. |
| The sheet includes undergraduates, graduate students, post-baccs, postdocs, faculty, and staff. | Do not assume all posters qualify for the same student award. |
| No poster number, board location, session assignment, acceptance status, award eligibility, or judge roster is supplied. | Obtain organizer decisions before assigning locations or configuring awards. |

## What the app already provides

- An event model, poster records, and event-scoped unique project numbers.
- Judge access codes, assignments, mobile scoring, feedback, score review, and
  ranked results exports.
- Withdrawal and reinstatement of presentations.
- An admin project import route and project-management screen.

Important gaps verified in the source:

- **Public lookup:** project-list routes require an admin or judge login. Add a
  public read-only route and a deliberately limited response schema.
- **Import validation:** `csv_import.py` compares required source headers such as
  `Title` with mapped model fields such as `Project_Title`. A correctly formatted
  CSV is reported as missing `Title`, `First_Name`, and `Last_Name`. Correct this
  before relying on imports.
- **Repeat imports and numbering:** imports insert new rows and use counts to
  generate numbers. They do not reconcile repeat uploads or reserve numbers
  safely after withdrawals/deletions or manually supplied numbers.
- **Presenter metadata:** the model expects one first/last name pair and has no
  dedicated institution or co-presenter display field.
- **Conference identity:** landing, login, and judge-shell screens hard-code GPSA
  branding and March 13. The event has one date field, while ASM runs two days.
- **Event bootstrap:** no event-creation screen or rubric-creation route exists.
  Startup automatically seeds GPSA data on an empty database and attempts a
  historical GPSA roster repair even when an event already exists.
- **Scoring assumptions:** score limits of 0–3 exist in the database, API, and UI.
  Results rank by mean judge total, with total score used as a secondary sort.
  There is no attendee ballot workflow or session voting window.
- **Deployment:** checked-in Docker Compose uses PostgreSQL. SQLite is supported
  for direct local runs. Preserve the established deployment path for this event.

## Delivery sequence

### 1. Reconcile the roster and establish numbering

Deliverable: an organizer-reviewed roster with explicit inclusion decisions and
a permanent mapping from source submissions to accepted presentations.

1. Preserve the supplied workbook unchanged. Read its ten source columns and
   produce an import preview plus an exceptions list.
2. Trim incidental whitespace and normalize matching keys while preserving the
   original titles, names, and institution text.
3. Resolve the two duplicate candidates, the talk-only applicants, and any
   late additions or withdrawals with Paul. Do not automatically choose the last
   submission when it changes the applicant's position or preferences.
4. Review name parsing, including compound surnames and the co-presenter record.
5. Once inclusion and layout are settled, assign numbers such as `P-001` through
   `P-NNN`. The three-digit format also sorts correctly above 99.
6. Record the agreed initial ordering. Use presenter surname and title as a
   provisional ordering only if Paul has no session or subject grouping needs.
7. Freeze issued numbers. Later additions receive the next unused number,
   withdrawals retain their reserved number, and edits do not renumber posters.

Keep poster identity separate from board location. For example, poster `P-042`
can occupy board `B-17`. If numbers are intended to identify physical boards
directly, agree that convention and the room layout before printing.

### 2. Make conference setup and import repeatable

Deliverable: an ASM deployment that can restart or reload a corrected roster
without introducing GPSA records, duplicate posters, or changed numbers.

- Add an explicit startup option to disable historical GPSA event seeding and its
  roster-repair hook. Keep admin-account provisioning separate.
- Create ASM through a small, repeatable setup command. Give it its own event ID,
  database/volume, secrets, and deployment configuration.
- For the short deadline, use a reviewed workbook-to-import conversion command.
  A new general-purpose XLSX upload interface can wait.
- Fix CSV required-header validation. Allocate numbers from reserved values,
  validate duplicates before writing, and handle database conflicts cleanly.
- Match repeat imports through a retained import manifest tied to `Project_ID`.
  Use normalized email/title combinations only to propose initial matches. Do
  not use sheet row numbers as permanent identity or silently create a new
  poster when a title changes.
- Provide preview counts and errors before committing an import. Commit the
  reviewed batch atomically. Re-uploading identical data must create zero new
  posters and preserve issued numbers.
- Add focused schema changes with an explicit migration; startup currently
  stamps Alembic head, so stamping alone must not substitute for applying changes.

Proposed data mapping:

| Workbook field | Destination/use |
| --- | --- |
| `Abstract title ` | `Project_Title`, preserving punctuation and scientific names |
| `Presenting author` | Preserve in a new `Presenter_Display_Name`; retain reviewed first/last fields for existing screens and exports |
| `Presenting author email address` | Private organizer contact data; retain multiple contacts in the source/manifest and choose a primary contact only after review |
| `Institution` | New `Institution` field; retain original text and use a reviewed normalization map for display/filtering |
| `PI/ Lab name` | `Advisor_Name` for existing administrative use |
| `Your current position` | Retain in the import manifest; add an application field only if award groups need it |
| Requested presentation formats | Import-review evidence, separate from final acceptance/category |
| Specialty and abstract text | Preserve in the source/manifest; import into the app only if needed for assignment or an approved public program |
| Timestamp | Provenance and revision review; not a poster number |
| Organizer-assigned number and location | Existing `Project_Number` and `Table_Number` |

Keep `Category = Poster` for accepted ASM posters. Oral presentations, award
groups, and poster sessions should not be represented by the legacy `Art` type.

### 3. Add public poster lookup and setup materials

Deliverable: a mobile-friendly page that attendees can reach without an account.

- Add a prominent `Find my poster` entry point and public `/posters` route.
- Search by presenter name, either co-presenter, title, and poster number. Show
  institution as a distinguishing detail and optional filter.
- Make the number the main result, followed by full presenter display name,
  title, institution, and confirmed location/session instructions.
- Show a useful no-match message directing attendees to registration staff.
- Return only published, active ASM posters through an event-scoped public API.
  Use a separate public schema that excludes email addresses, judge codes,
  scores, feedback, and internal roster-review notes.
- Update ASM name, October 31–November 1 dates, venue, browser title, and visible
  screen copy from one conference metadata source. A configuration-level date
  range is sufficient for this deployment; avoid a calendar redesign.
- Export a public numbered directory and printable number/board labels. Put a
  QR code for the public lookup on registration signage. The directory and
  labels must use the same persisted roster as the lookup page.
- Keep a printable alphabetical list at registration in case connectivity fails.

### 4. Configure rubric judging

Deliverable: designated judges use their access codes to review assigned ASM
posters, submit the approved rubric, and provide optional feedback. Administrators
monitor completed reviews and export award results.

- Obtain criteria, score scale, judge roster, conflict rules, coverage target,
  award eligibility, and tie rules. Reuse access-code login and assignments.
- Create the ASM rubric with a repeatable setup command. Freeze its criteria
  before scoring opens so all reviews use the same rubric.
- Keep the 0–3 scale only if Paul approves it. Other scales require coordinated
  database, backend, scoring UI, override UI, and display changes.
- Validate that submitted criteria belong to the project's event and rubric,
  are unique, and form a complete submission before counting it in results.
- Ensure judge project-detail reads are scoped to that judge's event, as writes
  already are. Decide whether assignments restrict scoring or merely guide it.
- Agree award groups, minimum completed reviews, aggregation, and ties. Current
  sequential ranks and average/total sorting are not an agreed award policy.
- Treat three judges per poster as a planning option. At 109 posters that means
  327 completed reviews, so feasibility depends on the judge roster and available
  time.
- Show rubric results and coverage to administrators. Publish winners only
  through the organizer's agreed release process.

### 5. Add attendee voting

Deliverable: eligible attendees can identify posters by number or search, submit
a ballot, and receive confirmation. Administrators can open and close voting,
monitor participation, and export attendee-choice results.

Recommended access approach, pending organizer agreement: registration staff give
each eligible attendee one unique voting code. Attendees do not need a new
account. A public QR code leads to the voting entry page; it does not grant a
ballot by itself. The abstract workbook cannot provide the voter roster because
many attendees may not submit abstracts.

- Add a `Vote for posters` entry point alongside `Find my poster` and the judge
  login. Public lookup remains available without a voting code.
- Provide an admin workflow to generate and print voter codes, record issuance,
  and revoke or replace a lost code while preserving one ballot entitlement.
  Use random, unguessable codes, store their hashes, and limit login attempts.
- Give voters a distinct authentication role and token storage key. Voting
  credentials must never grant judge/admin access or overwrite a judge login on
  a shared device.
- Agree how many posters each attendee may choose, whether choices are ranked,
  whether attendees can vote for their own posters, and whether ballots can be
  changed before closing. One submitted ballot per attendee per agreed voting
  round is the proposed baseline; browser cookies alone cannot enforce this.
- Use the same persisted poster identities and numbers as lookup and judging.
  Include confirmed session information so attendees know when to visit a poster.
- Show selected posters and remaining choices, require an explicit submit action,
  and provide a clear saved confirmation. Show the saved ballot on return.
- Enforce voter eligibility, ballot size, distinct selections, eligible active
  posters, event membership, and opening/closing times on the server. Handle
  duplicate clicks and network retries without counting another ballot.
- Confirm the treatment of a poster withdrawn after votes are cast. Retain the
  recorded history and exclude withdrawn posters from awards unless organizers
  explicitly decide otherwise.
- Keep totals private until voting closes. Admins can monitor ballots submitted
  and operational problems during the session without a public live leaderboard.
- Export attendee vote totals separately from rubric totals. Agree ties and
  award eligibility before announcing an attendee-choice winner. Combining vote
  totals with rubric scores would require an explicitly agreed weighting rule.

Proposed backend resources:

| Resource | Responsibility |
| --- | --- |
| `Voting_Round` | Event, ballot rules, opening/closing timestamps, and status |
| `Voter` | Event-scoped voting entitlement, code hash, issuance/revocation status |
| `Ballot` | One submission per voter and round, enforced by a unique constraint; submission/update timestamps |
| `Ballot_Selection` | Selected `Project_ID` values, unique within a ballot; rank only if ranked voting is chosen |

Use UUIDs for main entities and integer keys for ballot selections, following
repository conventions. Validate that voter, round, and selected posters belong
to the same event. Save a whole ballot atomically. Any allowed edit replaces its
selections atomically; concurrent submissions must not bypass the unique ballot
constraint. Keep administrator corrections auditable.

The supplied draft schedule lists poster session I on October 31, 3:45–5:00 p.m.,
and session II, 5:00–6:15 p.m., both with voting, in Vandal Ballroom. It also lists
an awards ceremony November 1 at 4:50 p.m. Confirm whether voting is confined to
those sessions or continues into Sunday. Use `America/Los_Angeles` for explicit
open/close times across this weekend's daylight-saving transition.

Decide whether there is one conference-wide voting round or separate rounds for
the two poster sessions. For a shared attendee-choice award, a common closing
time after both sessions gives attendees a chance to consider posters from both.
If separate session rounds are used, explicitly define ballot allowances and how
the results determine awards.

### 6. Rehearse and launch

Proposed work sequence, contingent on roster and evaluation-rule decisions:

| Date | Target |
| --- | --- |
| Tuesday, October 27 | Resolve roster discrepancies, agree numbering and physical placement, and obtain rubric and ballot rules. |
| Wednesday, October 28 | Finish import fixes, isolated ASM setup, numbering preview, and public lookup. |
| Thursday, October 29 | Review the numbered roster with Paul, complete rubric judging and attendee voting, and rehearse both evaluation flows. |
| Friday, October 30 | Resolve rehearsal issues, freeze published numbers and evaluation rules, print poster materials and voter/judge codes, verify venue connectivity, and take a recoverable backup. |
| Saturday, October 31 | Support poster setup before the 3:20 p.m. mixer and the confirmed evaluation windows. |
| Sunday, November 1 | Close evaluation at the agreed time, export results before awards, and archive the final roster and database. |

All four workflows are required for the planned launch. If evaluation rules or
implementation miss rehearsal, flag the schedule risk and agree a fallback with
Barrie and Paul. Do not silently drop either evaluation workflow from scope.

## Acceptance checks

- Organizer-approved inclusion count reconciles to the import manifest. Every
  published poster has exactly one unique event-scoped number.
- Repeat import, title correction, late addition, withdrawal, and restart preserve
  existing numbers. A withdrawn number is never reused.
- Public search finds long names, compound surnames, either co-presenter, and
  posters numbered above 99. Empty/no-match states work on a phone.
- Public response fields exclude contact details, judge credentials, and scores.
  Requests cannot reveal another event's unpublished records.
- Printed numbers, alphabetical directory, public lookup, and judge records all
  agree on the same presentation identity and location.
- A fresh ASM installation and a restart contain no automatically added GPSA
  records. The historical GPSA deployment remains recoverable.
- For rubric judging, verify permissions, incomplete/invalid submissions,
  repeat submissions, coverage, award grouping, ties, and exported totals with a
  small known-answer rehearsal.
- For attendee voting, verify valid/invalid/revoked codes, entitlement-preserving
  replacement, duplicate selections, ballot limits, simultaneous submissions,
  retries, saved-ballot retrieval, and any allowed edits. Confirm server-enforced
  closing times, event isolation, eligibility, ties, and known-answer vote totals.
- A voter cannot access judging/admin routes. A judge's rubric submission and
  attendee ballot remain separate even if the same person holds both roles.
- Rehearse opening and closing the actual configured voting round(s). Confirm
  rubric and attendee-choice exports are clearly labeled and independently tally.
- Run the frontend build/lint and focused backend regression tests for changed
  behavior. Verify the public URL and QR code on a real phone, then confirm a
  backup can be restored into an isolated database.

## Decisions for Barrie and Paul

Confirmed: numbering, public lookup, rubric judging, and attendee voting.

1. Which abstracts become posters? Are talk-only applicants included, which
   duplicate versions should remain, and are there late additions beyond the file?
2. Does one number identify a presentation or a physical board, and how are the
   two poster sessions and room locations assigned?
3. What are the rubric criteria/scale, judge roster, conflicts, coverage target,
   award groups, aggregation, and tie rules?
4. Who may vote, how are codes issued, how many choices are allowed, are choices
   ranked, are self-votes or ballot edits allowed, and are there one or two voting
   rounds? What are the closing time, award groups, and tie rules?
5. Which public URL and host should serve ASM, and who owns roster changes and
   on-site support after numbers are published?

The first implementation milestone is a reviewed numbered roster and a working
public lookup. The second is working rubric judging and attendee voting against
that same roster, with separate results and a completed rehearsal.
