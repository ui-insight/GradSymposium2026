# GPSA Handoff Guide

## Purpose

This project is the GPSA Graduate Student Symposium judging application used for
the March 13, 2026 event. The goal of this handoff is to preserve enough
context that GPSA or a future technical maintainer can:

- redeploy the system,
- reopen it for a future symposium,
- understand the few places where the current product requires API or database
  work instead of admin UI clicks,
- archive the 2026 state safely.

## What To Preserve With The Archive

- This repository, including the `docs/` folder.
- A PostgreSQL database dump from the final production state.
- Exported final results spreadsheets from the admin Results page.
- The source roster spreadsheets used for the 2026 event.
- Any server notes for DNS, TLS, reverse proxy, SSH access, and hosting.
- A record of which commit hash was last deployed.

## Access Needed For A Future Restart

- Git access to this repository.
- SSH access to the deployment host if reusing the existing remote server flow.
- Permission to rotate application secrets.
- DNS and TLS control for the public symposium URL if it changes.

## Current System Realities

- The checked-in container deployment path is PostgreSQL-based.
- The backend still supports SQLite when run directly for local inspection or
  development.
- If the backend starts with an empty database, it auto-loads the built-in 2026
  event data from `backend/app/db/seed.py`.
- The admin UI supports judges, projects, assignments, score review, and result
  export, but it does not currently include event creation or rubric creation.
- The application expects exactly one active event in normal operation.
- A default admin account is created automatically when no admin exists:
  `admin` / `admin`.

## Recommended Future Reactivation Path

Use this path unless the application is being actively redeveloped.

1. Restore the archived PostgreSQL backup into a fresh deployment.
2. Rotate all secrets and the admin password.
3. Create the new event record through the admin API or FastAPI docs.
4. Clone the rubric rows from the 2026 event into the new event using the SQL
   example in [docs/OPERATIONS.md](OPERATIONS.md).
5. Mark the old event inactive and the new event active.
6. Load new judges and projects.
7. Distribute assignments, print access codes, and run the symposium.

This path keeps the historical 2026 data intact and avoids depending on the
hard-coded 2026 seed data for a future event.

## Risks To Surface During Handoff

- The checked-in `.env.dev` and `.env.prod` files contain historical secrets.
  They should not be reused as-is.
- There is no first-class "new year bootstrap" admin workflow in the UI today.
  The documented process depends on FastAPI `/docs` and a few SQL statements.
- Starting from a totally empty database without planning will recreate the 2026
  event data.

## Suggested Handoff Packet

- Link to this repository.
- Latest production database dump.
- Final event results export.
- Hosting/server contact information.
- The four docs in `docs/`.
- A short note stating whether GPSA intends to reuse the existing host or deploy
  somewhere new.
