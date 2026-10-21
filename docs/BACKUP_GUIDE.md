# Backup Guide

Your platform protects itself with automatic, off-site backups. This guide
explains how it works and how to run a backup by hand.

## What gets backed up

Every backup is a single file containing the three things needed to rebuild
everything:

1. The full database — all accounts, subscriptions, credits, and your data.
2. The `.env` file — all keys and settings.
3. The uploads folder — every file your users uploaded.

## Where backups go

Each backup is saved in up to three places at once, so a single failure never
loses your data:

- On the server itself (instant restore).
- Off-site on S3 / Cloudflare R2 (survives a server crash) — optional.
- A copy you keep yourself via Google Drive (rclone) — optional.

Local backups older than `BACKUP_KEEP_DAYS` (default 14) are removed
automatically so the disk never fills.

## Turn it on (one time)

```bash
./scripts/backup/install-cron.sh
```

This schedules a backup every night at 03:00. That's it.

## Run a backup right now

```bash
./scripts/backup/backup.sh
```

## Enable off-site copies (recommended)

Open `.env` and fill in any of these, then backups ship there automatically:

```
BACKUP_S3_BUCKET=my-bucket            # needs awscli on the host
BACKUP_S3_ENDPOINT=https://...        # for Cloudflare R2
BACKUP_RCLONE_REMOTE=gdrive:backups   # needs rclone configured
```

To restore from any backup, see RESTORE_GUIDE.md.
