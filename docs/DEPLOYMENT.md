# Deployment Guide

## Deployment Modes

This repository supports two practical run modes:

- Local development with a direct backend process and Vite frontend.
- Docker Compose deployment with PostgreSQL, which is the checked-in server path.

## Environment Variables

Use `.env.example` as the starting template.

Key variables:

- `GPSA_DATABASE_URL`: SQLAlchemy async database URL.
- `GPSA_SECRET_KEY`: JWT signing key. Change this for every real deployment.
- `GPSA_ACCESS_TOKEN_EXPIRE_MINUTES`: Admin and judge token lifetime.
- `GPSA_CORS_ORIGINS`: Comma-separated allowed origins.
- `GPSA_DEV_MODE`: `true` only for development.
- `HOST_PORT`: Public port exposed by Docker Compose.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: PostgreSQL container
  credentials.
- `POSTGRES_VOLUME_NAME`: App-specific Docker volume name. Use a unique value
  for each environment to prevent cross-application data collisions.

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend creates tables automatically on startup, ensures an admin account
exists, and stamps Alembic to the current schema.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://localhost:8000`.

## Local Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Open:

- App: `http://localhost:8080`
- API docs: `http://localhost:8080/docs`

Stop the stack with:

```bash
docker compose down
```

## Historical Remote Deploy Flow

The repository includes `deploy.sh`, which syncs the repo to the historical host
`openera.insight.uidaho.edu` and then runs `docker compose up -d --build`.

Usage:

```bash
./deploy.sh dev
./deploy.sh prod
```

This script expects:

- SSH access to `devops@openera.insight.uidaho.edu`
- `.env.dev` or `.env.prod` in the repo root
- Docker Compose on the remote host

Before reusing this flow:

- rotate all secrets in `.env.dev` and `.env.prod`,
- confirm the host, DNS, and reverse proxy are still correct,
- confirm the expected ports are still available.

## SQLite Option

SQLite is best treated as a local-only option for direct backend runs.

Example backend `.env` value:

```env
GPSA_DATABASE_URL=sqlite+aiosqlite:///./gpsa.db
GPSA_SECRET_KEY=dev-secret-change-me
GPSA_DEV_MODE=true
GPSA_CORS_ORIGINS=http://localhost:5173
```

The Docker Compose path in this repository does not use SQLite.

## Backups

Create a PostgreSQL dump from the running Compose stack:

```bash
mkdir -p backups
docker compose exec -T db \
  pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > "backups/gpsa-$(date +%Y-%m-%d).sql"
```

Restore a dump into a fresh database:

```bash
cat backups/gpsa-YYYY-MM-DD.sql | \
docker compose exec -T db psql -U "$POSTGRES_USER" "$POSTGRES_DB"
```

After a restore, restart the backend if needed:

```bash
docker compose restart backend
```

## Health Checks

Useful checks after deployment:

```bash
docker compose ps
curl -sI http://localhost:8080/
curl -sI http://localhost:8080/docs
```

If the app is exposed behind a reverse proxy, also confirm the external URL and
judge login page load correctly.
