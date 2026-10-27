# Archive Checklist

## Before Archiving

- Export final results from the admin Results page.
- Create and verify a PostgreSQL dump.
- Record the final deployed commit hash.
- Save any source spreadsheets used for judges, projects, or assignments.
- Save a copy of the final production `.env` outside the repository in a secure
  password manager or secrets vault.
- Note the production URL, host, exposed port, and SSH account used.

## Security Cleanup

- Rotate the admin password away from `admin`.
- Rotate `GPSA_SECRET_KEY`.
- Rotate PostgreSQL credentials before any future redeploy.
- Treat repository-tracked secrets in `.env.dev` and `.env.prod` as historical
  only and not safe for reuse.

## Recommended Archive Bundle

- Repository snapshot or tagged commit.
- Database dump.
- Final results export.
- Source spreadsheets.
- Server and DNS notes.
- A brief status note stating whether the app should be considered dormant,
  deprecated, or expected to return next year.

## Wake-Up Checklist

- Restore the database into a new PostgreSQL instance.
- Recreate a clean `.env` from `.env.example`.
- Generate new secrets and database passwords.
- Deploy with Docker Compose.
- Log in to `/docs` and create the next event.
- Clone the rubric set for that event.
- Load the new judges and projects.
- Test admin login, judge login, assignment flow, and result export before
  publishing the judge URL.
