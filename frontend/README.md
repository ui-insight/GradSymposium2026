# Frontend Notes

The frontend is a React 19 + TypeScript + Vite application that serves two user
flows:

- Admin dashboard at `/admin/...`
- Judge scoring portal at `/judge`

## Development

```bash
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to `http://localhost:8000`.

## Production Container

The production image:

- builds the Vite app,
- serves the static bundle with nginx,
- proxies `/api`, `/docs`, `/redoc`, and `/openapi.json` to the backend
  container.

## Important Behavior

- API calls are relative to `/api/v1`.
- Admin and judge tokens are stored in browser local storage.
- On `401`, the client clears local auth state and redirects the user back to
  the appropriate login page.

## Admin UI Coverage

Implemented in the UI:

- dashboard and QR code download,
- projects CSV import,
- judges list and one-by-one creation,
- printable access codes,
- assignment matrix and auto-distribute,
- rubric viewing,
- results review, export, and score override flow.

Not currently implemented in the UI:

- event creation,
- rubric creation for a new event,
- bulk judge import from CSV.

See [../docs/OPERATIONS.md](../docs/OPERATIONS.md) for the documented API and SQL
steps used during handoff.
