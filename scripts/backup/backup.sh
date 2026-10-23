#!/usr/bin/env bash
# =============================================================================
#  LAYER 1 — Automatic backup.
#  Captures the four things needed to restore everything:
#    1) PostgreSQL dump   2) .env   3) private uploads   4) curriculum sources
#  Then ships the archive to up to three places: local, S3/R2, and a copy the
#  customer keeps. Old local backups are rotated.
#
#  Usage:  ./scripts/backup/backup.sh
#  Cron :  see scripts/backup/install-cron.sh
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

# Load .env (for DB creds + offsite settings) without leaking it to logs.
get_env() { grep -E "^$1=" .env 2>/dev/null | head -1 | cut -d= -f2- | sed "s/[[:space:]]*#.*//"; }
POSTGRES_USER="$(get_env POSTGRES_USER)"
POSTGRES_DB="$(get_env POSTGRES_DB)"
COMPOSE_PROJECT_NAME="$(get_env COMPOSE_PROJECT_NAME)"
BACKUP_DIR="$(get_env BACKUP_DIR)"
BACKUP_KEEP_DAYS="$(get_env BACKUP_KEEP_DAYS)"
BACKUP_S3_BUCKET="$(get_env BACKUP_S3_BUCKET)"
BACKUP_S3_ENDPOINT="$(get_env BACKUP_S3_ENDPOINT)"
BACKUP_RCLONE_REMOTE="$(get_env BACKUP_RCLONE_REMOTE)"
PROJECT="${COMPOSE_PROJECT_NAME:-nuvira}"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-/root/backups/${PROJECT}}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-14}"
WORK="$(mktemp -d)"
ARCHIVE="${BACKUP_DIR}/backup_${PROJECT}_${STAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"
echo "==> Backup ${PROJECT} @ ${STAMP}"

# 1) Database dump (runs inside the db container — no host psql needed)
echo "  - dumping database…"
docker compose exec -T db pg_dump --no-owner --no-acl -U "${POSTGRES_USER:-nuvira}" "${POSTGRES_DB:-nuvira}" \
  > "${WORK}/database.sql"

# 2) .env (secrets + config)
[ -f .env ] && cp .env "${WORK}/.env" || echo "  ! no .env found"

# 3) uploads volume (copied out of the running backend container)
echo "  - copying uploads…"
docker compose cp backend:/app/uploads "${WORK}/uploads" 2>/dev/null || mkdir -p "${WORK}/uploads"

# 4) externally stored curriculum originals (not part of images or Git)
echo "  - copying curriculum sources…"
docker compose cp backend:/app/curriculum-content "${WORK}/curriculum-content" 2>/dev/null || mkdir -p "${WORK}/curriculum-content"

# pack
tar -czf "$ARCHIVE" -C "$WORK" .
rm -rf "$WORK"
sha256sum "$ARCHIVE" > "${ARCHIVE}.sha256"
SIZE="$(du -h "$ARCHIVE" | cut -f1)"
echo "  ✓ local backup: ${ARCHIVE} (${SIZE})"

# --- offsite copy 1: S3 / Cloudflare R2 (optional) ---
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
  echo "  - uploading to ${BACKUP_S3_BUCKET}…"
  AWS_ARGS=""
  [ -n "${BACKUP_S3_ENDPOINT:-}" ] && AWS_ARGS="--endpoint-url ${BACKUP_S3_ENDPOINT}"
  aws s3 cp "$ARCHIVE" "s3://${BACKUP_S3_BUCKET}/$(basename "$ARCHIVE")" $AWS_ARGS \
    && echo "  ✓ offsite (S3/R2) done" || echo "  ! S3/R2 upload failed"
fi

# --- offsite copy 2: rclone remote, e.g. customer's Google Drive (optional) ---
if [ -n "${BACKUP_RCLONE_REMOTE:-}" ]; then
  echo "  - uploading to ${BACKUP_RCLONE_REMOTE}…"
  rclone copy "$ARCHIVE" "${BACKUP_RCLONE_REMOTE}" \
    && echo "  ✓ offsite (rclone) done" || echo "  ! rclone upload failed"
fi

# rotation: delete local backups older than KEEP_DAYS
find "$BACKUP_DIR" -name "backup_${PROJECT}_*.tar.gz" -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "backup_${PROJECT}_*.tar.gz.sha256" -mtime +"$KEEP_DAYS" -delete 2>/dev/null || true

echo "✅ backup complete"
