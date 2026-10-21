#!/usr/bin/env bash
# Installs the backup (daily 03:00) + monitor (every 5 min) cron jobs.
# Usage:  ./scripts/backup/install-cron.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp)"
crontab -l 2>/dev/null | grep -v "saas-template backup/monitor" > "$TMP" || true
{
  echo "0 3 * * * cd ${DIR} && ./backup.sh  >> /var/log/saas-backup.log 2>&1  # saas-template backup/monitor"
  echo "*/5 * * * * cd ${DIR} && ./monitor.sh >> /var/log/saas-monitor.log 2>&1  # saas-template backup/monitor"
} >> "$TMP"
crontab "$TMP"; rm -f "$TMP"
echo "✅ cron installed:"
echo "   - daily backup  @ 03:00  -> /var/log/saas-backup.log"
echo "   - monitor       @ */5m   -> /var/log/saas-monitor.log"
crontab -l | grep "saas-template" || true
