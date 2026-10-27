# GPSA Symposium Scoring App

This repository contains the judging application used for the University of Idaho
GPSA Graduate Student Symposium held on March 13, 2026.

It is now documented for handoff and archive so GPSA or a future maintainer can
bring it back online when the symposium runs again.

## Start Here

- [ASM poster numbering and public lookup](docs/ASM_POSTER_LOOKUP.md)

- [Handoff guide](docs/HANDOFF.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Operations guide](docs/OPERATIONS.md)
- [Archive checklist](docs/ARCHIVE_CHECKLIST.md)
- [Backend notes](backend/README.md)
- [Frontend notes](frontend/README.md)

## Stack

- Frontend: React 19, TypeScript, Tailwind CSS v4, Vite
- Backend: FastAPI, async SQLAlchemy, Alembic
- Database: PostgreSQL for the checked-in Docker deployment flow
- Local-only option: SQLite is still supported for direct backend runs

## Important Handoff Notes

- The checked-in Docker deployment path uses PostgreSQL.
- If the backend starts against an empty database, it auto-seeds the built-in
  2026 symposium event, rubrics, judges, and projects from
  `backend/app/db/seed.py`.
- The admin UI does not currently expose event creation or rubric creation.
  Those steps are documented in [docs/OPERATIONS.md](docs/OPERATIONS.md).
- A default admin account is created automatically when no admin exists:
  `admin` / `admin`. Rotate that password before any future live use.
- Historical `.env.dev` and `.env.prod` files are present in the repository.
  Treat their credentials as compromised and rotate all secrets before reusing
  this project.

## Quick Local Run

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
```

The application will be available on `http://localhost:8080`.

## Repository Layout

```text
backend/     FastAPI app, models, schemas, services, migrations
frontend/    React app and nginx production container config
docs/        Handoff, deployment, operations, and archive documentation
deploy.sh    Remote Docker deployment helper for the historical host
```
