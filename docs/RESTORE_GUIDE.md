# Restore Guide

Bring your platform back from any backup — on the same server or a brand-new
one — with a single command. From a fresh machine to fully running takes
minutes.

## What you need

- A backup file (e.g. `backup_saas-template_20260615_030000.tar.gz`).
- A server with Docker installed.
- This project folder.

## Restore in one command

```bash
./scripts/backup/restore.sh /path/to/backup_xxx.tar.gz
```

It automatically:

1. Restores your `.env` (keys and settings).
2. Starts the database.
3. Loads all your data back into it.
4. Restores uploaded files.
5. Brings the whole platform online.

## Confirm it worked

```bash
curl http://localhost:8995/health/db
```

You should see `{"database": "ok"}`, and your site loads with all accounts and
data intact.

## Moving to a new server

This is the same as a restore — Docker makes it identical everywhere:

1. On the old server: `./scripts/backup/backup.sh`
2. Copy the backup file to the new server.
3. On the new server: `./scripts/backup/restore.sh backup_xxx.tar.gz`
4. Point your domain at the new server's IP.

Typical time: 20–30 minutes, most of it the file copy.
