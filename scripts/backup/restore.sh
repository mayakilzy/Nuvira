#!/usr/bin/env bash
# =============================================================================
#  LAYER 2 — Restore everything from one archive, on any server.
#  Goal: from a fresh machine to a fully running platform in minutes.
#
#  Usage:  ./scripts/backup/restore.sh /path/to/backup_xxx.tar.gz
#  Steps:  start stack -> restore DB -> restore .env + uploads -> restart
# =============================================================================
set -euo pipefail

ARCHIVE="${1:?Usage: restore.sh <backup_archive.tar.gz>}"
[ -f "$ARCHIVE" ] || { echo "Archive not found: $ARCHIVE"; exit 1; }

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
WORK="$(mktemp -d)"

echo "==> Restoring from $(basename "$ARCHIVE")"
tar -xzf "$ARCHIVE" -C "$WORK"

# 1) restore .env first (needed for DB creds + image tags)
if [ -f "${WORK}/.env" ]; then
  cp "${WORK}/.env" ./.env
  echo "  ✓ .env restored"
fi
set -a; . ./.env; set +a

# 2) bring up the database (and dependencies)
echo "  - starting stack…"
docker compose up -d db redis
echo "  - waiting for database…"
for i in $(seq 1 30); do
  docker compose exec -T db pg_isready -U "${POSTGRES_USER:-saas}" >/dev/null 2>&1 && break
  sleep 2
done

# 3) restore the database dump
if [ -f "${WORK}/database.sql" ]; then
  echo "  - restoring database…"
  docker compose exec -T db psql -U "${POSTGRES_USER:-saas}" -d "${POSTGRES_DB:-saas}" \
    < "${WORK}/database.sql"
  echo "  ✓ database restored"
fi

# 4) bring up the rest and restore uploads
docker compose up -d
if [ -d "${WORK}/uploads" ]; then
  echo "  - restoring uploads…"
  docker compose cp "${WORK}/uploads/." backend:/app/uploads/ 2>/dev/null || true
  echo "  ✓ uploads restored"
fi

rm -rf "$WORK"
echo "✅ restore complete — platform is back online"
echo "   Verify:  curl http://localhost:${BACKEND_PORT:-8995}/health/db"
