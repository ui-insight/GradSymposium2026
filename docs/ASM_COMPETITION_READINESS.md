# ASM competition readiness

Updated October 28, 2026. Dev: https://gpsa-dev.insight.uidaho.edu.

## Ready to review

- Public draft lookup: `/posters`. The existing ASM source roster remains 108
  candidates, with 15 inclusion decisions still pending (11 talk-only rows and
  four rows in two possible duplicate pairs). Public dev preview is enabled by
  Barrie's request. Preview visibility does not approve acceptance or eligibility.
- Admin `/admin/competition`: event selection, readiness checks, nullable rules,
  explicit organizer confirmation, open/close controls, and live complete-review
  coverage. Links preserve the selected event throughout administration.
- Admin Projects: separate judging and voting eligibility and award-group
  membership, source flags, inclusion approval, corrections and withdrawal.
- Admin Rubrics: editable criteria and descriptions, derived maximum score,
  confirmation lock, and integer scores within 0–5. Each criterion retains its
  own limits; historical GPSA and synthetic 0–3 rubrics keep their original scale.
  Paul’s ASM rubric has Research question, Methods, Results and Presentation,
  each 0–5 (20 points total), with score meanings and inline judge rubric help.
- Judge access codes, assigned-project menu, complete-rubric scoring, optional
  feedback, and saved confirmation. The judge header uses its own event metadata.
- Judge name confirmation: existing names are prefilled after the first code
  login, and returning confirmed judges go straight to their projects. **Edit
  name** remains available in the header. Confirmation persists across reloads;
  names are trimmed, required and limited to 100 characters per field. Codes are
  personal: sharing a code shares the same identity and saved work.
- Name corrections preserve judge IDs, codes, assignments, scores, feedback and
  explicit conflicts. They flag the judge in Admin Judges for mentor-conflict
  review and show the name before the pending corrections. After checking relationships in
  **Mentor conflicts**, resolve the current eligible relationships, then use
  **Finish review of corrected judge name**. A stale displayed name or roster
  cannot clear a newer correction's flag. This flag prompts organizer review;
  it does not infer conflicts or silently remove existing assignments. Organizer
  name corrections also require the judge to confirm the corrected name.
- Mentor conflict review compares each judge with the full PI/lab text, presenter
  and title. Explicit decisions are **No conflict confirmed**, **Conflict
  recorded**, or **Needs Paul's input**, with a required source/reason. Missing
  mentors and unmatched names stay unreviewed until an organizer supplies a
  decision. Changes to names, PI/lab, presenter, title, institution or roster
  eligibility make earlier review decisions stale. Recorded conflicts still
  block assignments and scores during a recheck.
- Admin CSV uploads preview recruited judges and mentor decisions before applying
  any rows. Imports with errors apply nothing, and a changed roster/review state
  requires a fresh preview. Existing identities require explicit Judge_ID values;
  possible name/email duplicates are flagged, never merged automatically.
- Manual and automatic assignments enforce event membership, active status,
  confirmed eligibility and recorded conflicts. Distribution balances assignment
  loads, preserves existing assignments and reports shortages. This is not a
  subject-expertise or automatically inferred conflict matcher.
- Results count complete, valid reviews only. The organizer chooses average or
  sum, review target, groups, and shared or manually resolved ties. Grouped events
  require choosing an award group for ranks. Ranks remain provisional while judging is open, while any eligible presentation
  in the selected group/category lacks its target, or when ties need manual resolution. Excel exports retain target and provisional labels.
- Attendee `/vote`: separate voter authentication, search, selection review,
  explicit submission, saved ballot and permitted edits. The backend enforces
  distinct eligible selections, event scope, self-vote policy and exact times.
- Admin Voting: draft rounds, rule readiness, scheduled opening/closing,
  registration-reference code issuance and printable cards, affiliation review,
  replacement/revocation, participation counts and closed-round CSV totals.
  Codes are random; only hashes are stored. Replacement retains the entitlement
  and its ballots, invalidating the old code and sessions. Download new codes
  before leaving the issuance page; they cannot be retrieved later.
- Closed or expired open rounds show **Attendee choice: top 10 by votes** in
  Admin Voting. This uses unweighted attendee vote counts, separate from rubric
  judging. Equal counts share a vote rank, and additional posters tied across
  position ten appear explicitly below the ten-row report. The report CSV includes
  both sections and labels cutoff ties. **Review complete tally** retains all
  eligible posters and the full CSV export. Zero-vote posters remain visible;
  poster-number ordering does not break ties or select award winners. Reports
  follow current eligibility, exclude withdrawals and preserve ballot history.

One voting entitlement represents an organizer-approved registration. Staff must
use a stable unique reference for each person; the application cannot identify a
person issued two different references. A public QR code only opens the entry
page. It does not grant a ballot. Bulk issuance deliberately leaves affiliations
unconfirmed; confirm a non-presenter or all affiliated posters individually.

## Upload judges and review mentors

Complete **Final roster review** before distributing real assignments. It records
explicit inclusion decisions, duplicate supersession provenance and the organizer's
exact-roster sign-off separately from competition eligibility. Review and upload
final changes, compare the accepted-only directory, and download the count/sign-off
report for the private operating guide. Names, mentor details or roster changes
may require mentor re-review; withdrawn and unresolved rows remain excluded from
assignments. The actual final ASM list and sign-off are still pending organizer
input. See `ASM_POSTER_LOOKUP.md` for the full workflow and publication gate.

Open **Mentor conflicts** in Administration and select the intended event. An
organizer works at a desk reviewing private roster information, so this workspace
uses a readable light layout and keeps full mentor and presenter names visible.

1. Expand **Import judge roster and mentor decisions** and download the judge CSV
   template. `First_Name` and `Last_Name` are required; `Email` and `Department`
   are optional. Blank `Judge_ID` creates a new personal judge account. To update
   an existing judge, copy its ID from the review page. Codes and existing work
   are retained. Missing optional columns preserve those contact fields on an
   explicit-ID update; empty cells in a supplied column clear the field.
2. Preview the CSV. Correct every error before applying. A possible existing name
   or email requires an explicit ID; a name match never establishes identity.
   New codes are available through the existing Judges/code-card workflow.
3. Select a judge and download that judge's decision sheet. It includes the stable
   ID, candidate number, full presenter/PI text and a review context. Confirm
   relationships with Paul, including co-mentors and other conflicts. Set
   `Decision` to `conflict`, `clear` or `needs_input`; enter a short confirmation
   source/reason/question in `Note`. Blank decisions are skipped. Keep full
   personal source material in private operator files, not the reason field.
4. Preview and apply reviewed decisions, or review individual relationships on
   screen. The preview identifies assignments that will be removed and retained
   historical scores that will be excluded. An existing conflict cannot be
   cleared by a CSV or a “no conflict” decision; resolve it explicitly in
   Competition setup. Changed context requires a new sheet and a fresh review.
5. Resolve pending roster eligibility before finishing a corrected judge's name
   review. Review current assignments and export any assignment shortages for
   judging setup (#13). Conflicts must not be relaxed to meet the target.

An unreviewed pair is not proof of no conflict. This workspace records organizer
evidence; existing assignment/scoring rules continue to enforce explicit
conflicts. With no recruited ASM judge list or mentor confirmations supplied yet,
the real mapping and final organizer sign-off for #10 remain pending. No real
mentor relationships are inferred, imported or signed off by implementation.

## Install the ASM rubric

The `20261028_judge_profile` migration adds nullable name confirmation/previous
name fields and a false-by-default conflict-review flag to existing judge records.
It does not recreate identities or rotate codes. Runtime startup also applies
these additive columns before stamping the migration head. Downgrade refuses to
discard populated confirmation/review state.

The `20261028_mentor_review` migration creates `Mentor_Review` for organizer
decisions, reviewer identity, time and the source context. Existing conflict and
assignment enforcement is reused. Downgrade refuses to discard saved decisions.
Runtime `create_all` also creates the new table on existing installations.

The `20261028_final_roster` migration creates append-only `Roster_Decision` and
`Roster_Signoff` tables. It preserves existing presentation records and numbers,
and refuses downgrade while either table contains review evidence. Existing
staged source events need explicit final decisions and current sign-off before
publication; the dev draft preview is unaffected by that final-publication gate.

On the intended ASM database, with historical seeding disabled, run from backend:

```bash
GPSA_SEED_HISTORICAL_EVENT=false .venv/bin/alembic upgrade head
GPSA_SEED_HISTORICAL_EVENT=false .venv/bin/python -m app.commands.configure_asm_rubric
```

Use the deployment’s Python/Alembic executables inside a backend container.
The schema migration widens the database score envelope and adds per-rubric
score meanings. It does not change existing criteria, score rows or overrides.
SQLite rebuilds the Score table while preserving IDs and audit references;
run the migration before startup if an external connection enables SQLite
foreign keys. The normal Alembic SQLite connection leaves foreign keys off
during this rebuild. PostgreSQL replaces the constraint in place.

The command targets the named October 31 ASM event, fills an empty unlocked
draft, and preserves criterion IDs on repeat runs. It refuses to overwrite a
different nonempty, locked or scored rubric. An identical rubric remains
unchanged even after scoring starts. It never activates the event, publishes
posters, confirms remaining competition rules or opens judging. Review the
rubric in admin and confirm/lock it as part of final competition setup.

Downgrading refuses to discard five-point criteria, scores, override history or
configured scale meanings. Back up the database before deployment. Rehearse with
synthetic records in an isolated database; do not score real ASM posters for QA.

## Safe rehearsal

Select **Synthetic rehearsal (not the ASM competition)** in Competition setup.
It is an inactive, separate event with three fictional presentations, three
fictional judges, six initial assignments and one example attendee entitlement.
It cannot appear in the active ASM public poster directory. Synthetic scoring
and voting are allowed only with dev mode enabled.

The example rubric has three criteria within 0–3, a two-review target, assignment
restrictions, average totals, shared ties, and a Demonstration award group. The
example ballot allows 1–2 unranked choices, excludes self votes, allows edits and
expires seven days after initial preparation. These are test fixtures, not
proposed or approved ASM rules. Each shared demo code represents one fictional
person; concurrent testers using the same code share that person's saved work.

1. Open `/judge`, enter a synthetic judge code and score an assigned presentation.
2. In Competition setup, verify complete reviews rise separately from assignments.
3. Score the same presentation as its other assigned judge; inspect the target
   and select **Demonstration** in Results to see ranking.
4. Open `/vote`, enter the synthetic attendee code, choose posters, review and
   save. Reload to verify persistence; edit while the example round is open.
5. In admin Voting, verify participation rises while totals remain hidden. Close
   only a disposable rehearsal round to inspect tally/export. A closed round
   cannot reopen; create another synthetic draft if needed.
6. Try the real ASM event: rules stay pending and opening is blocked.

Synthetic codes are in the private preparation output, not committed source.
Preparation is repeatable and does not reset scores, ballots, closed rounds,
operator assignments or eligibility decisions. It does not reopen expired demos.

```bash
# Run inside the dev backend after its schema upgrade/startup.
python -m app.commands.prepare_competition \
  --credentials /tmp/asm-rehearsal-access.json
```

Copy the output to the private operator directory before replacing containers;
restore the same file before a repeat preparation. Without it, preparation issues
another synthetic voter code and invalidates prior synthetic sessions.

## Decisions still needed

- Final accepted roster and count; duplicate versions (source rows 6/9 and
  92/109); inclusion of talk-only applicants; late changes; board locations and
  the two session assignments. Existing numbers remain reserved after withdrawal.
- Judges and supplied conflicts; confirmation/locking of Paul’s configured rubric;
  minimum reviews; whether assignments restrict scoring; eligibility and awards;
  aggregation, ties, release procedure and operational owner.
- Voter eligibility and unique registration roster/distribution policy; choices,
  ranked/unranked, self votes and edits; one round or session rounds; exact
  opening/closing instants; session-specific poster eligibility; award grouping,
  ranked weighting and ties; treatment of withdrawn presentations and revocations.
- ASM launch URL/deployment, support owner, real-device rehearsal and venue Wi-Fi.

Current voting eligibility is event-wide, so separate rounds share the eligible
poster pool. Session-restricted candidate pools, a ranked weighting formula,
separate attendee award groups, and automatic tie resolution would require
further implementation if selected. Current withdrawal behavior retains history
and excludes withdrawn posters from reported totals. Revoking a voting code
blocks future access and retains its existing ballot. These provisional behaviors
need organizer agreement before launch; no award winner is announced by the app.

Voting timestamps require an explicit UTC offset and are stored as instants.
Admin editors display the operator's local timezone. Confirm the schedule in
America/Los_Angeles, including the November 1 daylight-saving transition. Rules
freeze at first score (judging) or opening (voting); withdrawal and audited score
overrides remain operational tools. Close judging before changing eligibility or
award groups, and close open voting rounds before changing voting eligibility.

## Verification and operations

Automated checks cover migrations, permanent numbering, import repetition,
publication/privacy, complete-rubric validation, assignment/conflict enforcement,
coverage, award groups and ties, event/role isolation, concurrent score and ballot
submissions, ballot retries/edits, replacement/revocation, affiliation, deadlines,
rate limits, and repeatable synthetic preparation. Frontend lint/build and its
storage regression test run alongside browser rehearsals of actual controls.
Real old-phone and venue-network testing remains an organizer rehearsal step.

The login limiter is in-process and assumes the current single backend worker.
If deployment changes to multiple workers/replicas, move it to shared storage.
Server/database backups and private code exports are required before deployment
or conference opening. Rolling application code back does not mean downgrading
away competition data: the migration refuses to discard populated new tables or
eligibility decisions.

Dev uses its existing PostgreSQL volume; isolated local tests use SQLite.
Production and the historical GPSA event remain separate. Deploy a clean Git
archive, preserve `.env` and the database volume, and keep source spreadsheets,
email, private review files and credentials out of the release bundle. Do not run
the broad rsync deployment script against this working directory.
