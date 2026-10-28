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

One voting entitlement represents an organizer-approved registration. Staff must
use a stable unique reference for each person; the application cannot identify a
person issued two different references. A public QR code only opens the entry
page. It does not grant a ballot. Bulk issuance deliberately leaves affiliations
unconfirmed; confirm a non-presenter or all affiliated posters individually.

## Install the ASM rubric

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
