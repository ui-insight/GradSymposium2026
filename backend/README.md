# Backend Notes

The backend is a FastAPI application with async SQLAlchemy models and Alembic
configuration.

## Development

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Startup Behavior

On startup the backend:

- loads environment variables,
- creates database tables if needed,
- applies runtime schema checks,
- stamps Alembic to `head`,
- ensures an admin user exists,
- seeds the built-in 2026 symposium data if the database is empty.

## Important Caveats

- Empty databases are automatically seeded with the March 13, 2026 symposium
  data from `app/db/seed.py`.
- The default admin account is `admin` / `admin` until changed.
- The checked-in Docker deployment expects PostgreSQL.
- SQLite still works for direct local backend runs.

## Useful Endpoints

- `/api/v1/auth/login`
- `/api/v1/events`
- `/api/v1/projects`
- `/api/v1/judges`
- `/api/v1/assignments`
- `/api/v1/results`
- `/api/v1/scores`
- `/api/v1/judge`
- `/docs`

## Handoff Reference

For deployment and future symposium bootstrapping, use:

- [../docs/DEPLOYMENT.md](../docs/DEPLOYMENT.md)
- [../docs/OPERATIONS.md](../docs/OPERATIONS.md)
- [../docs/HANDOFF.md](../docs/HANDOFF.md)
