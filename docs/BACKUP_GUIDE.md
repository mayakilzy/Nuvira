# Nuvira Backup Guide

Nuvira backups contain the PostgreSQL dump, `.env`, and uploaded materials required for recovery. The backup script writes a SHA-256 sidecar and can copy the archive to S3/R2 and an rclone destination.

## Enable scheduled backups

After validating a manual backup and restore in isolation:

```bash
cd /root/apps/nuvira
./scripts/backup/install-cron.sh
```

## Run and verify a backup

```bash
cd /root/apps/nuvira
./scripts/backup/backup.sh
sha256sum -c /root/backups/nuvira/backup_nuvira_<timestamp>.tar.gz.sha256
```

The database dump uses `--no-owner --no-acl` so it can be restored safely under the Nuvira database role. Backup archives and checksum files must never be committed to Git.

## Off-site copies

Configure `BACKUP_S3_BUCKET`/`BACKUP_S3_ENDPOINT` and/or `BACKUP_RCLONE_REMOTE` in `.env`. Retain at least one copy outside the production server and periodically rehearse restoration to empty, isolated Nuvira volumes.
