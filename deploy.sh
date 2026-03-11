#!/bin/bash
set -euo pipefail

# ── GPSA Deployment Script ───────────────────────────────────────────
# Usage: ./deploy.sh <prod|dev>
#
# Deploys the GPSA app to the remote server via Docker Compose.
#   prod → gpsa.insight.uidaho.edu    (port 9400)
#   dev  → gpsa-dev.insight.uidaho.edu (port 9410)

REMOTE_USER="devops"
REMOTE_HOST="openera.insight.uidaho.edu"
APP_NAME="gpsa"

ENV="${1:-}"
if [[ "$ENV" != "prod" && "$ENV" != "dev" ]]; then
    echo "Usage: $0 <prod|dev>"
    exit 1
fi

ENV_FILE=".env.${ENV}"
PROJECT_NAME="${APP_NAME}-${ENV}"

if [[ "$ENV" == "prod" ]]; then
    REMOTE_DIR="${APP_NAME}"
else
    REMOTE_DIR="${APP_NAME}-${ENV}"
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Error: ${ENV_FILE} not found"
    exit 1
fi

echo "==> Deploying GPSA ($ENV) to ${REMOTE_HOST}"
echo "    Project: ${PROJECT_NAME}"
echo "    Remote dir: ${REMOTE_DIR}"

# ── Sync project files to remote ────────────────────────────────────
echo "==> Syncing files..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" "mkdir -p ${REMOTE_DIR}"

rsync -avz --delete \
    --exclude '.git' \
    --exclude 'node_modules' \
    --exclude '__pycache__' \
    --exclude '.venv' \
    --exclude '*.db' \
    --exclude 'dist' \
    --exclude '.env' \
    --exclude '.env.prod' \
    --exclude '.env.dev' \
    --exclude 'plan.md' \
    ./ "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/"

# ── Copy the correct env file ───────────────────────────────────────
echo "==> Copying ${ENV_FILE}..."
scp "${ENV_FILE}" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/.env"

# ── Build and start containers on remote ─────────────────────────────
echo "==> Building and starting containers..."
ssh "${REMOTE_USER}@${REMOTE_HOST}" bash -s <<EOF
cd ${REMOTE_DIR}
docker compose -p ${PROJECT_NAME} down --remove-orphans 2>/dev/null || true
docker compose -p ${PROJECT_NAME} up -d --build
echo "==> Waiting for services to be healthy..."
sleep 5
docker compose -p ${PROJECT_NAME} ps
EOF

echo ""
echo "==> Deployment complete!"
if [[ "$ENV" == "prod" ]]; then
    echo "    URL: https://gpsa.insight.uidaho.edu"
    echo "    Port: 9400"
else
    echo "    URL: https://gpsa-dev.insight.uidaho.edu"
    echo "    Port: 9410"
fi
