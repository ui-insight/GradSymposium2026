#!/bin/sh
set -e

export PYTHONPATH=/app:${PYTHONPATH:-}

# ── Wait for PostgreSQL ──────────────────────────────────────────────
python -c "
import os, sys, socket, time

db_url = os.environ.get('GPSA_DATABASE_URL', '')
if 'postgresql' not in db_url and 'postgres' not in db_url:
    sys.exit(0)

try:
    at_part = db_url.split('@')[1]
    host_port = at_part.split('/')[0]
    if ':' in host_port:
        host, port = host_port.rsplit(':', 1)
        port = int(port)
    else:
        host = host_port
        port = 5432
except Exception:
    host, port = 'db', 5432

max_wait = 30
waited = 0
while waited < max_wait:
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        print(f'PostgreSQL is ready at {host}:{port}')
        sys.exit(0)
    except OSError:
        print(f'Waiting for PostgreSQL at {host}:{port}... ({waited}s)')
        time.sleep(2)
        waited += 2

print(f'ERROR: PostgreSQL not ready after {max_wait}s')
sys.exit(1)
"

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
