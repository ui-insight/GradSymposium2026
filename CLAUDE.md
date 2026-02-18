# CLAUDE.md — GradSymposium2026

## What This Project Is

A standalone web application for the GPSA Graduate Student Symposium at the University of Idaho. Judges score student poster and art presentations; scores auto-tally; admins view ranked results.

**Stack:** React 19 + TypeScript + Tailwind CSS v4 (frontend) / Python FastAPI + async SQLAlchemy + SQLite (backend)

## Key Conventions

### Database
- Column names: PascalCase_With_Underscores (e.g., `Project_ID`, `First_Name`)
- Primary keys: UUID strings for main entities, autoincrement integers for junction/score tables
- SQLite for dev and production (scale is small — max ~40k score rows)

### Backend
- Ruff formatter, 88 char line length
- Async everywhere: `await db.execute(select(Model).where(...))`
- One file per resource: `models/project.py`, `schemas/project.py`, `api/v1/projects.py`
- Schemas: `Create`, `Update` (optional fields), `Read` (with `from_attributes=True`)

### Frontend
- Functional components with hooks, no class components
- Tailwind CSS v4 utility classes only — no component library
- TypeScript interfaces mirror Pydantic schemas

### Auth
- **Admin:** username/password → JWT stored in localStorage
- **Judge:** 6-char access code → JWT stored in localStorage
- Two separate auth flows, both produce JWTs

## Rubric Structure

### Art (3 criteria, 0-3 each, max 9 pts)
1. Craftsmanship/Technical Skill
2. Creativity and Originality
3. Communication of Ideas and Theme

### Poster (12 criteria in 3 groups, 0-3 each, max 36 pts)
**Poster Content:** Layout, Introduction, Research Question, Methodology, Results, Graphics
**Communication Skills:** Cohesive Flow, Impact, Engaging Presentation
**Professional Presentation:** Technical Language, Q&A Handling, Formatting

## Development

```bash
# Backend
cd backend && source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend
cd frontend && npm run dev
```

**Dev credentials:** admin/admin (admin), judge access codes visible in admin dashboard

## Git Conventions
- Branch naming: `feature/...`, `fix/...`
- Commit messages: imperative mood, under 72 chars
