# GradSymposium2026

A web application for judging and scoring presentations at the University of Idaho GPSA Graduate Student Symposium.

**Event:** March 13, 2026 — Bruce Pitman Center, International Ballroom

## Features

- **Admin dashboard** — manage events, projects, judges, rubrics, and view results
- **Judge portal** — mobile-friendly scoring interface using simple access codes
- **Two rubric types** — Art (3 criteria, max 9 pts) and Poster (12 criteria, max 36 pts)
- **CSV import** — bulk upload student projects from a spreadsheet
- **Real-time results** — aggregated rankings by category with Excel export
- **Access code auth** — judges log in with a 6-character code, no password needed

## Tech Stack

- **Frontend:** React 19, TypeScript, Tailwind CSS v4
- **Backend:** Python FastAPI, async SQLAlchemy, SQLite
- **Auth:** JWT (admin login + judge access codes)

## Quick Start

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

### Dev Credentials

- **Admin:** `admin` / `admin`
- **Judge access codes:** see the Judges page in the admin dashboard after seeding

## Project Structure

```
backend/
  app/
    api/v1/       # FastAPI route handlers
    auth/         # JWT and password utilities
    db/           # Database engine, base, seed data
    models/       # SQLAlchemy ORM models
    schemas/      # Pydantic request/response schemas
    services/     # Business logic (CSV import, results, export)
    config.py     # Settings
    main.py       # FastAPI app entry point

frontend/
  src/
    api/          # API client modules
    components/   # Reusable UI components
    pages/        # Route-level page components
    types/        # TypeScript interfaces
```

## License

MIT
