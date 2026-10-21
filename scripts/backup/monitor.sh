#!/usr/bin/env bash
# =============================================================================
#  LAYER 3 — Monitoring & early warning.
#  Checks: site up? · database up? · disk space? · SSL expiry?
#  On any failure -> sends an email alert via Resend (same key the app uses).
#
#  Usage:  ./scripts/backup/monitor.sh
#  Cron :  every 5 minutes (see install-cron.sh)
# =============================================================================
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
set -a; [ -f .env ] && . ./.env; set +a

ALERT_TO="${ALERT_EMAIL:-${FIRST_ADMIN_EMAIL:-}}"
DISK_THRESHOLD="${DISK_ALERT_PCT:-80}"
SSL_DOMAIN="${SSL_CHECK_DOMAIN:-}"     # e.g. saas.agentcraft.info
SSL_WARN_DAYS="${SSL_WARN_DAYS:-14}"
PROBLEMS=()

# 1) site responding?
HEALTH_URL="http://localhost:${BACKEND_PORT:-8995}/health"
curl -fsS --max-time 10 "$HEALTH_URL" >/dev/null 2>&1 \
  || PROBLEMS+=("API not responding at ${HEALTH_URL}")

# 2) database responding?
docker compose exec -T db pg_isready -U "${POSTGRES_USER:-saas}" >/dev/null 2>&1 \
  || PROBLEMS+=("PostgreSQL is not ready")

# 3) disk usage
USED=$(df --output=pcent / | tail -1 | tr -dc '0-9')
[ "${USED:-0}" -ge "$DISK_THRESHOLD" ] \
  && PROBLEMS+=("Disk usage at ${USED}% (threshold ${DISK_THRESHOLD}%)")

# 4) SSL expiry (optional)
if [ -n "$SSL_DOMAIN" ]; then
  END=$(echo | openssl s_client -servername "$SSL_DOMAIN" -connect "${SSL_DOMAIN}:443" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
  if [ -n "$END" ]; then
    SECS=$(( ( $(date -d "$END" +%s) - $(date +%s) ) / 86400 ))
    [ "$SECS" -le "$SSL_WARN_DAYS" ] && PROBLEMS+=("SSL for ${SSL_DOMAIN} expires in ${SECS} days")
  fi
fi

# all good -> quiet exit
[ ${#PROBLEMS[@]} -eq 0 ] && { echo "$(date '+%F %T') ✓ all checks passed"; exit 0; }

# build alert
BODY="<h2>⚠️ ${COMPOSE_PROJECT_NAME:-saas-template} alert</h2><ul>"
for p in "${PROBLEMS[@]}"; do BODY="${BODY}<li>${p}</li>"; echo "ALERT: $p"; done
BODY="${BODY}</ul><p>$(date)</p>"

# send via Resend
if [ -n "${RESEND_API_KEY:-}" ] && [ -n "$ALERT_TO" ]; then
  curl -fsS -X POST https://api.resend.com/emails \
    -H "Authorization: Bearer ${RESEND_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "{\"from\":\"${EMAIL_FROM:-noreply@example.com}\",\"to\":[\"${ALERT_TO}\"],\"subject\":\"⚠️ Platform alert\",\"html\":\"${BODY//\"/\\\"}\"}" \
    >/dev/null 2>&1 && echo "  → alert emailed to ${ALERT_TO}" || echo "  ! failed to send alert"
fi
exit 1
