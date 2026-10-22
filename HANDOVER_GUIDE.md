# Nuvira Handover Guide

Nuvira is a self-contained educational platform with user accounts, subject entitlements, learning progress, uploaded course materials, AI chat, billing, credits, and administration.

## First-time setup

1. Clone `https://github.com/mayakilzy/Nuvira.git` into `/root/apps/nuvira/`.
2. Ensure the Nginx Proxy Manager network exists, then copy `.env.example` to `.env`.
3. Replace all database, JWT, admin, AI, email, OAuth, and payment placeholders.
4. Build the frontend with `PUBLIC_API_URL=https://api.nuvira.agentcraft.info`.
5. Start with `docker compose up -d`; do not add host port mappings.
6. Route `nuvira.agentcraft.info` to `frontend:3000` and `api.nuvira.agentcraft.info` to `backend:8000` through the shared proxy network.
7. Run database migrations and the smoke tests in `docs/DEPLOYMENT.md`.
8. Enable backups only after a successful backup/restore rehearsal.

## Isolation rules

- Never attach Nuvira to another application's PostgreSQL, Redis, uploads, or internal network.
- Only frontend and backend join the shared proxy network.
- PostgreSQL, Redis, worker, and named volumes belong exclusively to Nuvira.
- Never copy a legacy `.env` wholesale; create new production secrets and migrate only reviewed data.

## Backups and migration

- Daily backup: `./scripts/backup/backup.sh`
- Restore guide: `docs/RESTORE_GUIDE.md`
- Legacy data transfer: `docs/SUZANNA_TO_NUVIRA_MIGRATION.md`

The migration is a separately authorized operation. It was documented but not executed during engineering preparation.

## Safety

Keep `.env`, database dumps, uploaded files, and backup archives outside Git. Before any upgrade, record the deployed commit and image digests, create a verified backup, and confirm rollback steps without deleting named volumes.
